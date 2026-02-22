#pragma once

#include <Arduino.h>

namespace agent {

struct OtaResult {
  bool ok = false;
  String errorCode;
  String message;
  String actualSha256;
};

OtaResult performOta(const String& url, const String& expectedSha256);

}  // namespace agent
