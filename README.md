# Clyra-Vendor — Redmi Pad Pro 5G (`ruan`)

<p align="center">
  <img src="https://img.shields.io/badge/Android-16%20(API%2036)-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android 16" />
  <img src="https://img.shields.io/badge/Kernel-6.6.162--Clyra--Flip-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Kernel 6.6.162" />
  <img src="https://img.shields.io/badge/Platform-Qualcomm%20SM7435-D32F2F?style=for-the-badge&logo=qualcomm&logoColor=white" alt="Qualcomm SM7435" />
  <img src="https://img.shields.io/badge/GPU-Adreno%20710%20%7C%20Vulkan%201.3-E91E63?style=for-the-badge&logo=vulkan&logoColor=white" alt="Vulkan 1.3" />
  <img src="https://img.shields.io/badge/CAF-Code%20Aurora%20Forum-orange?style=for-the-badge" alt="CAF Supported" />
</p>

---

## Overview

**Clyra-Vendor** provides proprietary vendor binaries, firmware configs, and open-source HAL definitions for the **Redmi Pad Pro 5G (`ruan`)**, built on the **Qualcomm SM7435 (Snapdragon 7s Gen 2 / `parrot`)** mobile platform. 

This tree upgrades the stock vendor baseline to **Android 16 (API Level 36)**, unlocks **Vulkan 1.3** and **Qualcomm Neural Network (QNN) GPU acceleration**, conforms to **Code Aurora Forum (CAF)** standards, and provides seamless first-class compatibility with the [**Clyra-Flip Linux 6.6.162 Kernel**](https://github.com/isiddharthsarkar/Clyra-Flip).

---

## Device & Platform Specifications

| Specification | Details |
|---|---|
| **Device Model** | Redmi Pad Pro 5G (`24074RPD2G`) |
| **Codename** | `ruan` |
| **SoC / Chipset** | Qualcomm SM7435 (Snapdragon 7s Gen 2 / `parrot`) |
| **CPU Architecture** | `arm64-v8a` (`armv8-a` generic) |
| **GPU Architecture** | Adreno 710 |
| **Vulkan API** | Vulkan 1.3 (`android.hardware.vulkan.version-1_3.xml`) |
| **AI / GPU Engine** | Qualcomm QNN GPU acceleration runtime (`libQnnGpu*.so`) |
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

### 2. Adreno 710 GPU & Vulkan 1.3 Stack
- **Vulkan 1.3 Activation**: Added `proprietary/vendor/etc/permissions/android.hardware.vulkan.version-1_3.xml` (Feature version `4206592`) enabling full modern Vulkan 1.3 runtime support on Adreno 710.
- **Qualcomm Neural Network (QNN) Acceleration**: Integrated 64-bit QNN GPU binaries (`libQnnGpu.so`, `libQnnGpuNetRunExtensions.so`, and `libQnnGpuProfilingReader.so`) for on-device machine learning and accelerated compute workloads.

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

---

## Repository Structure

```text
Clyra-Vendor/
├── Android.bp                  # Soong namespace imports & prebuilt definitions
├── BoardConfigVendor.mk        # Platform, architecture, kernel & CAF variables
├── vendor.mk                   # Complete PRODUCT_COPY_FILES & property mappings
├── proprietary/                # Extracted and upgraded proprietary blobs
│   ├── odm/                    # Board configs, sensor configs, panel LUT tables
│   ├── vendor/                 # Core HALs, binaries, Adreno/Vulkan libraries, QNN
│   └── vendor_dlkm/            # Loadable kernel modules (.ko) for Clyra-Flip
├── firmware/                   # Firmware profile and partition metadata
├── scripts/                    # Zero-root EROFS unpacker & maintenance tools
│   ├── extract_super.py        # Python sparse/raw super.img unpacker
│   ├── make_vendor_tree.py     # EROFS filesystem tree builder
│   ├── extract-vendor.sh       # Pipeline orchestration script
│   └── tests/                  # Self-contained test suite (26 passing tests)
└── .github/                    # CI verification workflows
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

## Verification & Self-Test Suite

This repository includes a test suite verifying super image unpacking, EROFS parsing, fixture validation, and makefile generation:

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
-----------------------------------------------
Result: 26 passed, 0 failed
```

---

## Credits & Acknowledgements

- **[Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip)**: Primary Linux 6.6.162 GKI kernel tree for `ruan`.
- **Qualcomm Technologies, Inc. & Code Aurora Forum**: Open-source HALs, kernel headers, and platform architecture.
- **LineageOS & TheMuppets**: Hardware compatibility references for SM7435 sister platforms.
- **Xiaomi**: Original stock OS3.0.306.0.WFSINXM firmware images.
