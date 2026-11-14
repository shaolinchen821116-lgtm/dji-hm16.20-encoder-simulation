// Local experiment policy; retain HM copyright notices in source and COPYING.
#ifndef DJI_CAMERA_POLICY_H
#define DJI_CAMERA_POLICY_H
struct CameraPolicy {
  static bool interSize(unsigned w) {return w == 8 || w == 16 || w == 32;}
  static bool intraSize(unsigned w) {return w == 8 || w == 16 || w == 32;}
  static bool intraNxN() {return true;}
  static bool amp() {return true;}
  static unsigned minInterTU() {return 4;}
  static unsigned maxInterTU() {return 16;}
};
#endif
