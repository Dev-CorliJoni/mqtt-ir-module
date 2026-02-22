#include "agent_mqtt.h"

#include "agent_commands.h"
#include "agent_pairing.h"
#include "agent_runtime_state.h"
#include "agent_state.h"

#include <algorithm>

namespace agent {

void onMqttMessage(char* topicChars, byte* payload, unsigned int length) {
  const String topic(topicChars ? topicChars : "");
  if (topic == "ir/pairing/open") {
    handlePairingOpen(payload, length);
    return;
  }
  if (topic.startsWith("ir/pairing/accept/")) {
    handlePairingAccept(topic, payload, length);
    return;
  }
  if (topic.startsWith("ir/pairing/unpair/")) {
    handlePairingUnpair(topic, payload, length);
    return;
  }

  String command;
  if (!parseCommandTopic(topic, command)) {
    return;
  }

  DynamicJsonDocument doc(kMqttBufferSize);
  if (!parsePayloadObject(payload, length, doc)) {
    return;
  }
  handleCommand(command, doc.as<JsonObjectConst>());
}

bool connectMqtt() {
  if (gRuntimeConfig.mqttHost.isEmpty()) {
    return false;
  }

  gMqttClient.setServer(gRuntimeConfig.mqttHost.c_str(), gRuntimeConfig.mqttPort);
  gMqttClient.setBufferSize(kMqttBufferSize);
  gMqttClient.setKeepAlive(60);
  gMqttClient.setCallback(onMqttMessage);

  bool connected = false;
  if (gRuntimeConfig.mqttUser.length() > 0) {
    connected = gMqttClient.connect(
        gAgentId.c_str(),
        gRuntimeConfig.mqttUser.c_str(),
        gRuntimeConfig.mqttPass.c_str(),
        topicStatus().c_str(),
        1,
        true,
        "offline");
  } else {
    connected = gMqttClient.connect(gAgentId.c_str(), topicStatus().c_str(), 1, true, "offline");
  }

  if (!connected) {
    return false;
  }

  gMqttClient.publish(topicStatus().c_str(), "online", true);
  gMqttClient.subscribe("ir/pairing/open");
  gMqttClient.subscribe(topicPairingAccept().c_str());
  gMqttClient.subscribe(topicPairingUnpair().c_str());
  gMqttClient.subscribe(topicCommands().c_str());
  publishState();
  markActivity();
  applyPowerMode();
  return true;
}

}  // namespace agent
