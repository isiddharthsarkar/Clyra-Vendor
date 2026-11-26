# Clyra-Vendor — Redmi Pad Pro 5G (`ruan`)

<p align="center">
  <img src="https://img.shields.io/badge/Android-16%20(API%2036)-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android 16" />
  <img src="https://img.shields.io/badge/Architecture-Pure%2064--Bit%20(arm64)-8A2BE2?style=for-the-badge&logo=arm&logoColor=white" alt="Pure 64-Bit" />
  <img src="https://img.shields.io/badge/Kernel-6.6.162--Clyra--Flip-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Kernel 6.6.162" />
  <img src="https://img.shields.io/badge/Platform-Qualcomm%20SM7435-D32F2F?style=for-the-badge&logo=qualcomm&logoColor=white" alt="Qualcomm SM7435" />
  <img src="https://img.shields.io/badge/GPU-Adreno%20710%20%7C%20Vulkan%201.3-E91E63?style=for-the-badge&logo=vulkan&logoColor=white" alt="Vulkan 1.3" />
  <img src="https://img.shields.io/badge/ROMs-HyperOS%203%20%7C%20OneUI%208%20%7C%20ColorOS%20%7C%20AOSP%2016-green?style=for-the-badge" alt="Multi-ROM" />
  <img src="https://img.shields.io/badge/Cross--Port-Garnet%20%26%20Pad%202%20Pro-00ACC1?style=for-the-badge" alt="Cross-Port Ready" />
</p>

---

## Overview

**Clyra-Vendor** provides proprietary vendor binaries, firmware configs, and open-source HAL definitions for the **Redmi Pad Pro 5G (`ruan`)**, built on the **Qualcomm SM7435 (Snapdragon 7s Gen 2 / `parrot`)** mobile platform. 

This tree is rebuilt to a **Pure 64-Bit (`arm64-v8a`) architecture**, upgrades the vendor baseline to **Android 16 (API Level 36)**, unlocks **Vulkan 1.3** and **Qualcomm Neural Network (QNN) GPU acceleration**, conforms to **Code Aurora Forum (CAF)** standards, and enables seamless compatibility for running **HyperOS 3+**, **OneUI 8+**, **ColorOS 15/16+**, **AOSP 16+**, **Redmi Pad 2 Pro (`organ` / `flute`)**, and **Redmi Note 13 Pro 5G (`garnet`)** cross-ports alongside the [**Clyra-Flip Linux 6.6.162 Kernel**](https://github.com/isiddharthsarkar/Clyra-Flip).

---

## Device & Platform Specifications

| Specification | Details |
|---|---|
| **Device Model** | Redmi Pad Pro 5G (`24074RPD2G` / `24074RPD2I`) |
| **Codename** | `ruan` (5G) / Compatible with `dizi` (Wi-Fi) |
| **Cross-Port Targets** | `garnet` (Redmi Note 13 Pro 5G), `organ` / `flute` (Redmi Pad 2 Pro) |
| **Compatible ROMs** | **HyperOS 3+**, **OneUI 8+**, **ColorOS 15/16+**, **AOSP 16+ (GSI / LineageOS 23)** |
| **SoC / Chipset** | Qualcomm SM7435 (Snapdragon 7s Gen 2 / `parrot`) |
| **CPU Architecture** | **`arm64-v8a` (Pure 64-bit only / No 32-bit overhead)** |
| **Form Factor** | `tablet` (`ro.build.characteristics=tablet`) |
| **GPU Architecture** | Adreno 710 |
| **Vulkan API** | Vulkan 1.3 (`android.hardware.vulkan.version-1_3.xml`) |
| **AI / Compute Engine** | Qualcomm QNN acceleration suite (CPU, DSP, HTA, HTP) |
| **Target Android Release** | **Android 16** (API Level 36) |
| **Build Fingerprint** | `Redmi/ruan/ruan:16/BP2A.250305.002/OS3.0.306.0.WFSINXM:user/release-keys` |
| **Stock Firmware Source** | `ruan_in_global_images_OS3.0.306.0.WFSINXM_20261021.0000.00_16.0_in_e97cbecd4c.tgz` |
| **Primary Kernel** | [Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip) (Linux 6.6.162 / GKI 3.1) |

---

## Key Enhancements

### 1. Android 16 (API 36) Baseline
- Upgraded `ro.vendor.build.version.release=16`, `ro.vendor.build.version.sdk=36`, `ro.vndk.version=36`, `ro.board.api_level=36`, and `ro.vendor.api_level=36`.
- Aligned ODM configurations across all regional SKUs (`n83ucn`, `n83ucnes`, `n83ugl`, `n83uin`, `n83uja`, `n83upin`) with Android 16 target IDs (`BP2A.250305.002`).
- Configured makefiles with `BOARD_API_LEVEL := 36` and `PRODUCT_SHIPPING_API_LEVEL := 36`.

### 2. Adreno 710 GPU & Vulkan 1.3 Stack (Updated via Garnet SM7435 Blobs)
- **Updated Adreno 710 Drivers**: Integrated newer Adreno graphics drivers (`vulkan.adreno.so`, `libGLESv2_adreno.so`, `libllvm-qgl.so`, `libadreno_app_profiles.so`, `libadreno_utils.so`) built from newer Qualcomm BSP sources (`EV031.36.08.34`, July 2025) via sister device `garnet` (LineageOS 24 / Android 16).
- **Vulkan 1.3 Activation**: Added `proprietary/vendor/etc/permissions/android.hardware.vulkan.version-1_3.xml` (Feature version `4206592`) enabling modern Vulkan 1.3/1.4 runtime support.
- **Complete Qualcomm Neural Network (QNN) & Hexagon DSP Stack**: Integrated the full QNN acceleration suite (CPU, DSP, HTA, and HTP backends: `libQnn*.so`, `libSnpeDspV65Stub.so`, and `libhta_hexagon_runtime_qnn.so`) for accelerated on-device AI compute.
- **Display & Color Pipeline**: Added Xiaomi Gralloc utilities (`libcom.xiaomi.grallocutils.so`), display QoS (`libdisplayqos.so`), and Qualcomm Display Color services (`vendor.display.color@1.0.so` through `1.7.so`).
- **Media & Codec2 Subsystem**: Added Android 16 Codec2 VINTF manifest (`c2_manifest_vendor.xml`) and updated hardware/software codec filters (`libqc2*.so`, `libqcodec2*.so`).
- **Bluetooth Audio & Sound Enhancement**: Updated Bluetooth Audio session HALs (`vendor.qti.hardware.bluetooth_audio@2.0/2.1-impl.so`, `libbluetooth_audio_session_qti*.so`) and Xiaomi sound modules (`lib_misound_asc.so`, `libaudiocloudctrl.so`, `libaudioroute_ext.so`).

### 3. Clyra-Flip Kernel (Linux 6.6.162) Direct Support
- Matches the kernel configuration and KMI requirements of [Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip):
  ```text
  TARGET_KERNEL_VERSION := 6.6.162
  TARGET_LINUX_KERNEL_VERSION := 6.6
  TARGET_KERNEL_CONFIG := gki_defconfig vendor/parrot_GKI.config vendor/ruan_GKI.config vendor/ruan_android16.config
  ```
- **`vendor_dlkm` Dynamic Modules**: Ingests all 28+ kernel loadable modules into `proprietary/vendor_dlkm/lib/modules/`, ensuring full hardware support for touch (`xiaomi_touch`), hall sensor (`xiaomi_hall`), audio amplifiers (`wsa881x`/`wsa883x`), and display controllers under GKI 3.1.

### 4. Code Aurora Forum (CAF) Architecture
- **Qualcomm Modular Android Architecture (QMAA)**: Enabled modular HAL overrides across Audio, Display, Media, Data, CVP, and Biometrics.
- **Audio & Display Stacks**: Configured for CAF ALSA, PAL HIDL, AGM HIDL, Gralloc 4, DRM PP, and HWC2.
- **Soong Namespaces**: Pre-configured in `Android.bp` and `vendor.mk`:
  - `hardware/xiaomi`
  - `hardware/qcom-caf/sm8450`, `common`, `wlan`, `bt`
  - `vendor/qcom/opensource/commonsys-intf/display`, `commonsys/display`, `display`
  - `vendor/qcom/opensource/audio-hal/primary-hal`, `pal`, `agm`
  - `vendor/qcom/opensource/data-ipa-cfg-mgr`, `dataservices`
  - `vendor/qcom/opensource/vibrator`, `thermal-engine`, `power`, `location`, `usb`

### 5. Pure 64-Bit Architecture & Cross-Port Targets (Garnet & Redmi Pad 2 Pro)
- **Elimination of 32-Bit Overhead**: Removed all 32-bit legacy blobs, trimming repository bloat and eliminating 32-bit zygote RAM overhead.
- **`TARGET_ARCH := arm64`**: Configured `BoardConfigVendor.mk` with pure 64-bit architecture (`TARGET_2ND_ARCH :=` unset, `TARGET_USES_64_BIT_BINDER := true`).
- **Garnet & Redmi Pad 2 Pro Compatibility**: Seamless binder, HIDL, and AIDL interoperability for cross-porting between `garnet` (Redmi Note 13 Pro 5G) and `ruan` / `organ` / `flute` (Redmi Pad 2 Pro).
- **Multi-ROM Support**: Native compatibility for **HyperOS 3+**, **OneUI 8+**, **ColorOS 15/16+**, and **AOSP 16+** (LineageOS 23 / GSI).

### 6. Removal of Xiaomi Locks & Security Restrictions
- **DM-Verity (AVB) Unlocked**: Removed strict Android Verified Boot (`avb=vbmeta_system`, `avb`) partition signature enforcement from `fstab.default` and `fstab.emmc`.
- **Forced Encryption Unlocked**: Stripped proprietary Qualcomm/Xiaomi `wrappedkey_v0` hardware-bound encryption tokens from userdata mounts.
- **ADB & Root Debugging Enabled**: Configured `ro.adb.secure=0`, `ro.secure=0`, `ro.debuggable=1`, and `persist.sys.usb.config=adb` for instant, unrestricted early-boot ADB access.
- **Xiaomi DRM & Telemetry Daemons Neutralized**: Disabled execution of Xiaomi background tracking daemons (`mrmd`, `mimd-service`, `mtdservice`, `mfidoca`, `mlipay`, `tidaservice`, `vsimservice`).

---

## Repository Structure

```text
Clyra-Vendor/
├── Android.bp                  # Soong namespace imports & prebuilt definitions
├── Android.mk                  # Target symlink generation (Qualcomm RFS & WLAN)
├── BoardConfigVendor.mk        # Platform, architecture, kernel & CAF variables
├── vendor.mk                   # Complete PRODUCT_COPY_FILES & property mappings
├── proprietary/                # Extracted and upgraded proprietary blobs
│   ├── odm/                    # Board configs, sensor configs, panel LUT tables
│   ├── vendor/                 # Core HALs, binaries, Adreno/Vulkan libraries, QNN
│   └── vendor_dlkm/            # Loadable kernel modules (.ko) for Clyra-Flip
├── firmware/                   # Firmware profile and partition metadata
└── scripts/                    # Maintenance tools and automated test suites
    ├── extract_super.py        # Python sparse/raw super.img unpacker
    ├── make_vendor_tree.py     # EROFS filesystem tree builder
    ├── extract-vendor.sh       # Pipeline orchestration script
    └── tests/                  # Self-contained test suite (31 passing tests)
```

---

## Integration in ROM Trees

To integrate this vendor tree into an AOSP, LineageOS, or custom ROM build:

1. **Clone the repository** to `vendor/xiaomi/ruan`:
   ```bash
   git clone https://github.com/isiddharthsarkar/Clyra-Vendor.git -b main vendor/xiaomi/ruan
   ```

2. **Include in `BoardConfig.mk`** (in `device/xiaomi/ruan/BoardConfig.mk`):
   ```make
   include vendor/xiaomi/ruan/BoardConfigVendor.mk
   ```

3. **Inherit in `device.mk`** (in `device/xiaomi/ruan/device.mk` or `ruan.mk`):
   ```make
   $(call inherit-product, vendor/xiaomi/ruan/vendor.mk)
   ```

---

## Audit Findings

An audit pass (ruff, shellcheck, adversarial fixtures, and a full parse of the
committed tree) found the following. All are fixed and covered by regression
tests.

### High severity

| Bug | Impact |
|---|---|
| **`vendor.mk` paths did not exist.** All 3153 rules pointed at `vendor/ruan/proprietary/...` while blobs are committed at `proprietary/...`. | make parsed the file happily; the build would fail, or ship a vendor image containing no blobs. |
| **A comment inside a `+= \` continuation** ends the logical line, so GNU make silently discards the entire `PRODUCT_COPY_FILES` list. | Makefile looks valid, copies nothing. |
| **Truncated image on ENOSPC.** A failed write left a partial `vendor.img` that later steps would publish as complete. | Corrupt vendor partition that only fails at flash time. |

### Medium

| Bug | Impact |
|---|---|
| **32 blobs are 0 bytes** — `CAMERA_ICP.b1*`, `evass*.b1*`, `fs_config_dirs/files`, `passwd`, `group`. | Camera/DSP firmware and SELinux file contexts missing on device. Needs re-extraction; now detected by `scripts/tests/check_blobs.py`. |
| The broken-symlink test flagged **device-absolute** links (`/vendor/etc/...`) as errors. | A correct vendor tree failed its own suite. |
| Bad `--out-dir` (a file, read-only mount) raised a Python traceback. | Unhelpful, and left debris behind. |
| No free-space check before a multi-hour extraction. | Failure hours in, after most of the work. |
| Boot-image detection decompressed the 5 GiB archive **twice**. | Minutes of wasted I/O. |

### Low

Missing git identity failed mid-publish, after copying gigabytes. Planned-commit
count used floor+1 instead of ceiling.

### Verification tools

```bash
./scripts/tests/run-tests.sh                              # full suite
python3 scripts/tests/check_rules_resolve.py vendor.mk .  # every rule resolves
python3 scripts/tests/check_blobs.py . --strict           # empty / broken blobs
```

## Verification & Self-Test Suite

This repository includes a test suite verifying super image unpacking, EROFS parsing, fixture validation, makefile generation, 64-bit integrity, and service sanity:

```bash
./scripts/tests/run-tests.sh
```

```text
1. fixture generation: PASS
2. independent oracle (upstream lpunpack): PASS
3. extractor matches oracle byte-for-byte: PASS
4. payload lands in correct partitions: PASS
5. sparse image decompression: PASS
6. slot-suffixed metadata: PASS
7. tree builder & makefile generation: PASS
8. integrity checks & device.json coherence: PASS
9. tree integrity & 64-bit architecture verification: PASS (5/5)
-----------------------------------------------
Result: 31 passed, 0 failed
```

---

## Credits & Acknowledgements

- **[Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip)**: Primary Linux 6.6.162 GKI kernel tree for `ruan`.
- **Qualcomm Technologies, Inc. & Code Aurora Forum**: Open-source HALs, kernel headers, and platform architecture.
- **LineageOS & TheMuppets**: Hardware compatibility references for SM7435 sister platforms.
- **Xiaomi**: Original stock OS3.0.306.0.WFSINXM firmware images.
