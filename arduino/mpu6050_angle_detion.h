目前偵測程式如下 ，請減少在邊界附近快速切換的狀態，至少要相隔2秒

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h> // 需要包含 math.h 來使用 atan2 和 M_PI

Adafruit_MPU6050 mpu;

int currentOrientation = 0; // 追蹤當前邏輯上的方向
int lastSentOrientation = -1; // 追蹤上次發送的方向

// 角度邊界 (以度為單位)
// 這些邊界定義了每個方向的 "中心區域" 為 90 度寬
// 例如, 0 度方向的範圍是 45 度到 135 度 (圍繞 Y+ 軸)
const float ANGLE_BOUND_POS_Y = 45.0;  // Y+ (0 度) 的下邊界 (相對於 X+ 軸)
const float ANGLE_BOUND_NEG_Y = 135.0; // Y+ (0 度) 的上邊界 / Y- (180 度) 的下邊界
const float ANGLE_BOUND_NEG_X = -135.0; // Y- (180 度) 的上邊界 / X- (270 度) 的下邊界
const float ANGLE_BOUND_POS_X = -45.0;  // X- (270 度) 的上邊界 / X+ (90 度) 的下邊界

// 最小加速度幅度閾值 (平方值, 避免開根號)
// 避免在感測器接近平放時因雜訊產生錯誤讀數
// 例如, 0.3g * 0.3g = 0.09 * (9.8*9.8) approx 8.6
// 可根據實際情況調整
const float MIN_ACCEL_MAG_SQUARED = 8.0; // (m/s^2)^2

void setup(void) {
  Serial.begin(9600);
  while (!Serial) delay(10);

  Serial.println("MPU6050 Orientation Detector (Angle Based)");

  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) delay(10);
  }
  Serial.println("MPU6050 Found!");

  // Optional: Set range and filter
  // mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
  // mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  delay(100);
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp); // Get new sensor events

  float ax = a.acceleration.x;
  float ay = a.acceleration.y;

  // 檢查 XY 平面上的加速度幅度是否足夠大
  float accel_mag_sq = ax * ax + ay * ay;
  if (accel_mag_sq < MIN_ACCEL_MAG_SQUARED) {
    // 幅度太小，可能接近平放，維持上一個狀態，避免錯誤觸發
    // 不做任何改變，也不發送新狀態
     delay(100); // 稍微等待一下
     return; // 跳過這次迴圈的後續判斷
  }

  // 計算加速度向量在 XY 平面的角度 (相對於 X 軸正方向)
  // atan2(y, x) 返回弧度 (-PI to +PI)
  float angle_rad = atan2(ay, ax);
  // 將弧度轉換為度 (-180 to +180)
  float angle_deg = angle_rad * 180.0 / M_PI;

  int detectedOrientation = -1; // 預設為未確定

  // --- 根據角度範圍確定方向 ---
  // ！！！非常重要！！！
  // 這裡的角度範圍需要根據你的 MPU6050 **實際安裝方向** 來調整。
  // 以下是一個假設的範例，假設：
  // - 螢幕標準橫向 (0度) 時，重力主要在 +Y 軸 (感測器 Y 軸朝上)
  // - 螢幕順時針轉 90度 (縱向) 時，重力主要在 +X 軸 (感測器 X 軸朝右)
  // 在這種情況下，角度映射如下：
  // - Y+ (0度): atan2(y,x) 接近 90 度。範圍: 45 到 135 度。
  // - X+ (90度): atan2(y,x) 接近 0 度。範圍: -45 到 45 度。
  // - Y- (180度): atan2(y,x) 接近 -90 度。範圍: -135 到 -45 度。
  // - X- (270度): atan2(y,x) 接近 +/-180 度。範圍: > 135 或 < -135 度。

  if (angle_deg > ANGLE_BOUND_POS_Y && angle_deg <= ANGLE_BOUND_NEG_Y) {
      detectedOrientation = 0; // 0 度 (Y+)
  } else if (angle_deg > ANGLE_BOUND_POS_X && angle_deg <= ANGLE_BOUND_POS_Y) {
      detectedOrientation = 1; // 90 度 (X+)
  } else if (angle_deg > ANGLE_BOUND_NEG_X && angle_deg <= ANGLE_BOUND_POS_X) {
      detectedOrientation = 2; // 180 度 (Y-)
  } else if (angle_deg > ANGLE_BOUND_NEG_Y || angle_deg <= ANGLE_BOUND_NEG_X) {
      detectedOrientation = 3; // 270 度 (X-)
  }

  /* // ---- Debugging: 打印角度和檢測到的方向 ----
  Serial.print("X: "); Serial.print(ax);
  Serial.print("\tY: "); Serial.print(ay);
  Serial.print("\tAngle: "); Serial.print(angle_deg);
  Serial.print("\tDetected: "); Serial.println(orientationToString(detectedOrientation));
  // ---- End Debugging ---- */


  // 只有當檢測到的方向有效 (-1 表示無效) 且與上次發送的方向不同時，才發送更新
  if (detectedOrientation != -1 && detectedOrientation != lastSentOrientation) {
    Serial.println(orientationToString(detectedOrientation)); // 發送 "0", "90", "180", 或 "270"
    lastSentOrientation = detectedOrientation; // 更新上次發送的方向
  }

  delay(150); // 稍微增加延遲，讓角度穩定，可以根據需要調整 (例如 100-300ms)
}

// 將方向代碼轉換為字串
String orientationToString(int orientation) {
  switch (orientation) {
    case 0: return "0";
    case 1: return "90";
    case 2: return "180";
    case 3: return "270";
    default: return "UNDEF"; // Undefined or -1
  }
}

