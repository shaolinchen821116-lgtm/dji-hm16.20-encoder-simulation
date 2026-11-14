// Local experiment policy; retain HM copyright notices in source and COPYING.
#ifndef DJI_CAMERA_POLICY_H
#define DJI_CAMERA_POLICY_H
struct CameraPolicy {
  static bool interSize(unsigned w) {return w == 8 || w == 16 || w == 32;}
  static bool intraSize(unsigned w) {return w == 8 || w == 16;}
  static bool intraNxN() {return false;}
  static bool amp() {return false;}
  static unsigned minInterTU() {return 8;}
  static unsigned maxInterTU() {return 16;}
};
#endif
