#include "agent_bootstrap.h"

#include "agent_state.h"

#include <WiFi.h>
#include <WiFiManager.h>

namespace agent {

void configureWifiAndRuntime() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(WIFI_PS_NONE);

  String mqttHost = gRuntimeConfig.mqttHost;
  String mqttPort = String(gRuntimeConfig.mqttPort);
  String mqttUser = gRuntimeConfig.mqttUser;
  String mqttPass = gRuntimeConfig.mqttPass;
  String txPin = String(gRuntimeConfig.irTxPin);
  String rxPin = String(gRuntimeConfig.irRxPin);

  WiFiManagerParameter paramMqttHost("mqtt_host", "MQTT Host", mqttHost.c_str(), 64);
  WiFiManagerParameter paramMqttPort("mqtt_port", "MQTT Port", mqttPort.c_str(), 6);
  WiFiManagerParameter paramMqttUser("mqtt_user", "MQTT User", mqttUser.c_str(), 64);
  WiFiManagerParameter paramMqttPass("mqtt_pass", "MQTT Password", mqttPass.c_str(), 64);
  WiFiManagerParameter paramTxPin("ir_tx_pin", "IR TX Pin", txPin.c_str(), 4);
  WiFiManagerParameter paramRxPin("ir_rx_pin", "IR RX Pin", rxPin.c_str(), 4);

  WiFiManager wm;
  wm.setConnectTimeout(20);
  wm.setConfigPortalTimeout(240);
  wm.addParameter(&paramMqttHost);
  wm.addParameter(&paramMqttPort);
  wm.addParameter(&paramMqttUser);
  wm.addParameter(&paramMqttPass);
  wm.addParameter(&paramTxPin);
  wm.addParameter(&paramRxPin);

  const unsigned int idSuffixStart = (gAgentId.length() > 4U) ? (gAgentId.length() - 4U) : 0U;
  const String apSsid = String("ESP32-IR-Setup-") + gAgentId.substring(idSuffixStart);
  const bool wifiOk = wm.autoConnect(apSsid.c_str());
  if (!wifiOk) {
    delay(1000);
    ESP.restart();
    return;
  }

  gRuntimeConfig.mqttHost = String(paramMqttHost.getValue());
  gRuntimeConfig.mqttHost.trim();
  gRuntimeConfig.mqttPort = parseMqttPort(String(paramMqttPort.getValue()), gRuntimeConfig.mqttPort);
  gRuntimeConfig.mqttUser = String(paramMqttUser.getValue());
  gRuntimeConfig.mqttUser.trim();
  gRuntimeConfig.mqttPass = String(paramMqttPass.getValue());
  gRuntimeConfig.mqttPass.trim();
  gRuntimeConfig.irTxPin = parsePin(String(paramTxPin.getValue()), gRuntimeConfig.irTxPin);
  gRuntimeConfig.irRxPin = parsePin(String(paramRxPin.getValue()), gRuntimeConfig.irRxPin);
  saveRuntimeConfig();
}

}  // namespace agent
