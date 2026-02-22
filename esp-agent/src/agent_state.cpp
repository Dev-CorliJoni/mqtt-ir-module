#include "agent_state.h"

#include <algorithm>
#include <cstdlib>
#include <cstdio>

namespace agent {

Preferences gPrefs;
WiFiClient gNetClient;
PubSubClient gMqttClient(gNetClient);

RuntimeConfig gRuntimeConfig;
String gAgentId;
String gPairingHubId;
bool gDebugEnabled = false;
bool gRebootRequired = false;
bool gLearningActive = false;
bool gEcoMode = false;
unsigned long gActiveUntilMs = 0;
unsigned long gLastStatePublishMs = 0;
unsigned long gNextReconnectAtMs = 0;
unsigned long gReconnectDelayMs = kMqttReconnectMinMs;
bool gPendingReboot = false;
unsigned long gRebootAtMs = 0;
String gPairingSessionId;
String gPairingNonce;

IRsend* gIrSender = nullptr;
IRrecv* gIrReceiver = nullptr;
decode_results gDecodeResults;

bool isValidPin(int pin) {
  return pin >= 0 && pin <= 39;
}

String normalizeSha256(const String& value) {
  String normalized = value;
  normalized.trim();
  normalized.toLowerCase();
  return normalized;
}

bool isHexSha256(const String& value) {
  if (value.length() != 64) {
    return false;
  }
  for (size_t i = 0; i < value.length(); i++) {
    const char c = value.charAt(i);
    const bool digit = (c >= '0' && c <= '9');
    const bool alpha = (c >= 'a' && c <= 'f');
    if (!digit && !alpha) {
      return false;
    }
  }
  return true;
}

String nowSecondsText() {
  const float seconds = static_cast<float>(millis()) / 1000.0f;
  return String(seconds, 3);
}

String topicState() {
  return String("ir/agents/") + gAgentId + "/state";
}

String topicStatus() {
  return String("ir/agents/") + gAgentId + "/status";
}

String topicCommands() {
  return String("ir/agents/") + gAgentId + "/cmd/#";
}

String topicPairingAccept() {
  return String("ir/pairing/accept/+/") + gAgentId;
}

String topicPairingUnpair() {
  return String("ir/pairing/unpair/") + gAgentId;
}

String topicPairingUnpairAck() {
  return String("ir/pairing/unpair_ack/") + gAgentId;
}

String topicResponse(const String& hubId, const String& requestId) {
  return String("ir/hubs/") + hubId + "/agents/" + gAgentId + "/resp/" + requestId;
}

void saveRuntimeConfig() {
  gPrefs.begin(kPrefsNamespace, false);
  gPrefs.putString("mqtt_host", gRuntimeConfig.mqttHost);
  gPrefs.putUShort("mqtt_port", gRuntimeConfig.mqttPort);
  gPrefs.putString("mqtt_user", gRuntimeConfig.mqttUser);
  gPrefs.putString("mqtt_pass", gRuntimeConfig.mqttPass);
  gPrefs.putInt("ir_tx_pin", gRuntimeConfig.irTxPin);
  gPrefs.putInt("ir_rx_pin", gRuntimeConfig.irRxPin);
  gPrefs.end();
}

void savePairingHubId(const String& hubId) {
  gPairingHubId = hubId;
  gPrefs.begin(kPrefsNamespace, false);
  gPrefs.putString("pair_hub_id", gPairingHubId);
  gPrefs.end();
}

void saveDebugFlag(bool enabled) {
  gDebugEnabled = enabled;
  gPrefs.begin(kPrefsNamespace, false);
  gPrefs.putBool("debug", gDebugEnabled);
  gPrefs.end();
}

void saveRebootRequired(bool required) {
  gRebootRequired = required;
  gPrefs.begin(kPrefsNamespace, false);
  gPrefs.putBool("reboot_req", gRebootRequired);
  gPrefs.end();
}

void loadPersistedState() {
  gPrefs.begin(kPrefsNamespace, false);
  gRuntimeConfig.mqttHost = gPrefs.getString("mqtt_host", "");
  gRuntimeConfig.mqttPort = gPrefs.getUShort("mqtt_port", kDefaultMqttPort);
  if (gRuntimeConfig.mqttPort == 0) {
    gRuntimeConfig.mqttPort = kDefaultMqttPort;
  }
  gRuntimeConfig.mqttUser = gPrefs.getString("mqtt_user", "");
  gRuntimeConfig.mqttPass = gPrefs.getString("mqtt_pass", "");
  gRuntimeConfig.irTxPin = gPrefs.getInt("ir_tx_pin", kDefaultIrTxPin);
  gRuntimeConfig.irRxPin = gPrefs.getInt("ir_rx_pin", kDefaultIrRxPin);
  gPairingHubId = gPrefs.getString("pair_hub_id", "");
  gDebugEnabled = gPrefs.getBool("debug", false);
  gRebootRequired = gPrefs.getBool("reboot_req", false);
  gPrefs.end();
}

uint16_t parseMqttPort(const String& value, uint16_t fallback) {
  String trimmed = value;
  trimmed.trim();
  if (trimmed.isEmpty()) {
    return fallback;
  }
  const long parsed = strtol(trimmed.c_str(), nullptr, 10);
  if (parsed < 1 || parsed > 65535) {
    return fallback;
  }
  return static_cast<uint16_t>(parsed);
}

int parsePin(const String& value, int fallback) {
  String trimmed = value;
  trimmed.trim();
  if (trimmed.isEmpty()) {
    return fallback;
  }
  const long parsed = strtol(trimmed.c_str(), nullptr, 10);
  if (!isValidPin(static_cast<int>(parsed))) {
    return fallback;
  }
  return static_cast<int>(parsed);
}

void markActivity() {
  gActiveUntilMs = millis() + kActiveWindowMs;
}

void scheduleReboot(unsigned long delayMs) {
  gPendingReboot = true;
  gRebootAtMs = millis() + delayMs;
}

bool parseCommandTopic(const String& topic, String& commandOut) {
  const String prefix = String("ir/agents/") + gAgentId + "/cmd/";
  if (!topic.startsWith(prefix)) {
    return false;
  }
  commandOut = topic.substring(prefix.length());
  commandOut.trim();
  return !commandOut.isEmpty();
}

bool parseAcceptTopic(const String& topic, String& sessionOut) {
  const String prefix = "ir/pairing/accept/";
  if (!topic.startsWith(prefix)) {
    return false;
  }
  const int lastSlash = topic.lastIndexOf('/');
  if (lastSlash <= 0) {
    return false;
  }
  const String agentFromTopic = topic.substring(lastSlash + 1);
  if (agentFromTopic != gAgentId) {
    return false;
  }
  sessionOut = topic.substring(prefix.length(), lastSlash);
  sessionOut.trim();
  return !sessionOut.isEmpty();
}

bool parsePayloadObject(const byte* payload, unsigned int length, DynamicJsonDocument& doc) {
  const DeserializationError error = deserializeJson(doc, payload, length);
  return !error && doc.is<JsonObject>();
}

int majorFromVersion(const String& version) {
  String normalized = version;
  normalized.trim();
  if (normalized.isEmpty()) {
    return -1;
  }
  const int dotIndex = normalized.indexOf('.');
  if (dotIndex < 0) {
    return normalized.toInt();
  }
  return normalized.substring(0, dotIndex).toInt();
}

String buildAgentId() {
  const uint64_t chip = ESP.getEfuseMac();
  char buffer[13];
  snprintf(buffer, sizeof(buffer), "%012llx", static_cast<unsigned long long>(chip & 0xFFFFFFFFFFFFULL));
  return String("esp32-") + String(buffer);
}

}  // namespace agent
