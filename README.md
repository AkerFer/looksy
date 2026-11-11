# Looksy Android 0.1.0 (test APK)

Download Looksy.apk and install on Android 7.0 or newer.
Universal APK: ARMv7, ARM64, x86_64. Size: 53258224 bytes.
Signed with a test Android debug key; this is not a Google Play release.

Source commit: [b1fae7d3c3fe72b14e4e138f7672fde5b77cba18](https://github.com/AkerFer/looksy/commit/b1fae7d3c3fe72b14e4e138f7672fde5b77cba18).
[Connection and build instructions](https://github.com/AkerFer/looksy/blob/b1fae7d3c3fe72b14e4e138f7672fde5b77cba18/mobile/README.md).
[Verification report](https://github.com/AkerFer/looksy/blob/b1fae7d3c3fe72b14e4e138f7672fde5b77cba18/docs/stage-7.md).

Backend must remain running. Enter the computer's private Wi-Fi IP and port
8000 on the app login screen; localhost on the phone points to the phone.
For a public backend use HTTPS. No backend credentials are embedded in the APK.

SHA-256: `bdf8eea86d288bc7e40ab7865bd506529b96627924c9c785c9590ce5415db46d`.
Signature verified with Android apksigner (v2). Unit/widget tests: 7 passed;
Dart mobile API client tested against actual Django. Physical phone/camera,
gallery and iOS have not been tested in the cloud environment.

[Download ZIP with APK](https://github.com/AkerFer/looksy/raw/refs/heads/apk/android-0.1.0/Looksy-0.1.0.zip). Extract the archive and open Looksy.apk on your Android phone.
