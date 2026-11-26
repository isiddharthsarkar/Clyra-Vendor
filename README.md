# Clyra-Vendor — Redmi Pad Pro 5G (`ruan`)

<p align="center">
  <img src="https://img.shields.io/badge/Android-16%20(API%2036)-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android 16" />
  <img src="https://img.shields.io/badge/Architecture-Pure%2064--Bit%20(arm64)-8A2BE2?style=for-the-badge&logo=arm&logoColor=white" alt="Pure 64-Bit" />
  <img src="https://img.shields.io/badge/Kernel-6.6.162--Clyra--Flip-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Kernel 6.6.162" />
  <img src="https://img.shields.io/badge/Platform-Qualcomm%20SM7435-D32F2F?style=for-the-badge&logo=qualcomm&logoColor=white" alt="Qualcomm SM7435" />
  <img src="https://img.shields.io/badge/GPU-Adreno%20710%20%7C%20Vulkan%201.3-E91E63?style=for-the-badge&logo=vulkan&logoColor=white" alt="Vulkan 1.3" />
  <img src="https://img.shields.io/badge/ROMs-HyperOS%203%20%7C%20OneUI%208%20%7C%20ColorOS%20%7C%20AOSP%2016-green?style=for-the-badge" alt="Multi-ROM" />
  <img src="https://img.shields.io/badge/Cross--Port-Garnet%20%26%20Pad%202%20Pro-00ACC1?style=for-the-badge" alt="Cross-Port Ready" />
  <img src="https://img.shields.io/badge/CI-Disabled%20(manual%20verification)-9E9E9E?style=for-the-badge" alt="CI Disabled" />
</p>

> **CI is disabled on this repository.** GitHub Actions is turned off at the
> repository level — see [Continuous Integration](#continuous-integration).
> All verification runs locally and offline via `./scripts/tests/run-tests.sh`.

---

## Overview

**Clyra-Vendor** provides proprietary vendor binaries, firmware configs, and
open-source HAL definitions for the **Redmi Pad Pro 5G (`ruan`)**, built on the
**Qualcomm SM7435 (Snapdragon 7s Gen 2 / `parrot`)** mobile platform. The blobs
are extracted from the official fastboot ROM and are **`arm64` only** — there is
no 32-bit userspace anywhere in the tree.

One vendor tree serves four devices. Because `ruan`, **`garnet`** (Redmi Note 13
Pro 5G) and **`organ` / `flute`** (Redmi Pad 2 Pro) all share SM7435 and the
64-bit-only rule, porting a ROM between them requires **no edits here** — see
[Cross-port support](#cross-port-support-garnet--organ--flute).

The tree targets **Android 16 (API Level 36)**, ships **Vulkan 1.3** and the
**Qualcomm Neural Network (QNN)** stack, conforms to **Code Aurora Forum (CAF)**
standards, and is intended to run alongside the
[**Clyra-Flip Linux 6.6.162 Kernel**](https://github.com/isiddharthsarkar/Clyra-Flip)
across **HyperOS 3+**, **OneUI 8+**, **ColorOS 15/16+** and **AOSP 16+**.

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
├── vendor.mk                   # PRODUCT_COPY_FILES (generated)
├── vendor-port.mk              # Drop-in entry point for any SM7435 port
├── proprietary/                # Extracted and upgraded proprietary blobs
│   ├── odm/                    # Board configs, sensor configs, panel LUT tables
│   ├── vendor/                 # Core HALs, binaries, Adreno/Vulkan libraries, QNN
│   └── vendor_dlkm/            # Loadable kernel modules (.ko) for Clyra-Flip
├── firmware/
│   ├── device.json             # Blob-source device + ROM metadata
│   ├── targets.json            # Cross-port targets (ruan/garnet/organ/flute)
│   └── vendor_list_ruan.txt    # Partitions to extract
└── scripts/
    ├── extract_super.py        # Python sparse/raw super.img unpacker
    ├── make_vendor_tree.py     # EROFS filesystem tree builder
    ├── generate_build_files.py # Regenerates every *.mk/*.bp from targets.json
    ├── extract-vendor.sh       # Pipeline orchestration script
    └── tests/                  # Self-contained suite (46 passing tests)
        ├── check_arch.py        # 64-bit-only enforcement, keeps DSP/GPU firmware
        ├── check_blobs.py       # 0-byte and broken-symlink detection
        └── check_rules_resolve.py # Every PRODUCT_COPY_FILES source exists
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

## Architecture: 64-bit only

This tree is **`arm64-v8a` only**. There is no 32-bit path anywhere: no
`lib/`, no 32-bit zygote, no `abilist32` entries, no `TARGET_2ND_ARCH`.

Verified by `scripts/tests/check_arch.py`:

```
64-bit ELFs            : 1816   (all AArch64)
32-bit userspace ELFs  : 0
```

`BoardConfigVendor.mk` pins this explicitly, including empty
`TARGET_2ND_ARCH`/`TARGET_CPU_ABILIST32` so the build system can never place a
32-bit library into the vendor image.

### About the 54 "32-bit" files in `vendor/firmware/`

They are **not ARM code and must not be removed.** Their ELF headers report:

| Count | `e_machine` | What it actually is |
|---|---|---|
| 34 | 94 | Qualcomm **Hexagon DSP** — camera (`CAMERA_ICP`) |
| 19 | 164 | Qualcomm **custom** — Adreno **ZAP** GPU shaders |
| 1 | 40 | ARM32 coprocessor firmware (legacy camera) |

These run on the GPU/DSP, never on the CPU. Deleting them because they look
"32-bit" bricks the camera and GPU. `check_arch.py` keeps them and only
enforces AArch64 for code that the application CPU executes.

---

## Cross-port support (garnet / organ / flute)

The blobs come from `ruan` (Redmi Pad Pro 5G), but every target below shares
the **SM7435 / `parrot`** platform and the 64-bit-only requirement, so one
vendor tree serves all of them.

| Codename | Device | Form factor | Role |
|---|---|---|---|
| `ruan` | Redmi Pad Pro 5G | tablet | blob source |
| `garnet` | Redmi Note 13 Pro 5G | phone | cross-port |
| `organ` | Redmi Pad 2 Pro | tablet | cross-port |
| `flute` | Redmi Pad 2 Pro 5G | tablet | cross-port |

The list lives in [`firmware/targets.json`](firmware/targets.json). Adding a
device is a single entry there — then regenerate:

```bash
./scripts/generate_build_files.py
```

That rewrites `vendor.mk`, `Android.mk`, `Android.bp`, `BoardConfigVendor.mk`
and `vendor-port.mk` from the data, so the codename filters can never drift
out of sync again. `--check` fails if the files on disk are stale (used in CI
and in the self-test).

### Porting a ROM to one of these devices

Nothing in this repository needs editing. In the device tree:

```make
# device/<vendor>/<codename>/device.mk
CLYRA_VENDOR_PATH := vendor/clyra/ruan-in-16.0
$(call inherit-product, $(CLYRA_VENDOR_PATH)/vendor-port.mk)
```

`vendor-port.mk` resolves `TARGET_DEVICE` against the supported set, so the
same tree builds for `ruan`, `garnet`, `organ` and `flute`. A device outside
that set is skipped cleanly rather than failing the build.

### What a port may still need to override

These genuinely differ between SM7435 devices and are exposed as variables a
port can set before inheriting:

| Variable | Why it differs |
|---|---|
| `CLYRA_WLAN_FW_DIR` | WLAN firmware subdir (`qca6750`, `qca6490`, …) |
| `TARGET_KERNEL_CONFIG` | per-device GKI fragments |
| Display panel config | `nt36532` on ruan/garnet; check organ/flute |

---

## Continuous Integration

**No CI runs on this repository, by design.**

| | |
|---|---|
| Workflows | `probe.yml`, `test.yml` — both `disabled_manually` |
| Active workflows | 0 |
| Committed workflow files | none (`.github/workflows/README.md` only) |

### Why it was stopped

Every run failed at dispatch with no steps executed:

> The job was not started because recent account payments have failed or your
> spending limit needs to be increased.

`runner_id: 0` on each attempt — the runner was never allocated. A red check in
that state reports nothing about the code, only about billing, so it was noise
that invited false confidence.

### What verifies the code instead

The suite is offline, needs no device, no network and no root, and finishes in
about a second:

```bash
./scripts/tests/run-tests.sh          # 46 assertions
```

Plus four standalone auditors, each usable on its own:

```bash
python3 scripts/tests/check_arch.py .              # 64-bit only, keeps DSP/GPU firmware
python3 scripts/tests/check_blobs.py . --strict    # 0-byte / broken-symlink blobs
python3 scripts/tests/check_rules_resolve.py vendor.mk .   # every rule has a source
python3 scripts/generate_build_files.py --check    # generated files != stale
```

### Re-enabling

Resolve the billing block in **Settings → Billing & plans**, then restore
`test.yml` from history (`git log --all -- .github/workflows/test.yml`).
Re-adding it while billing is blocked only recreates a permanently red check.

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

### Twenty-track audit (round 3)

Twenty independent audit tracks were run against the tree. Tracks 1-10 were
static analysis and structural checks; 11-20 were semantic checks against the
real blobs. Results:

| # | Track | Result |
|---|---|---|
| 1 | Ruff (bug-class rules) | clean after fixes |
| 2 | ShellCheck | clean after fixes |
| 3 | Python compile / logic | clean |
| 4 | Makefile parse | all 4 files parse |
| 5 | JSON / YAML validity | clean |
| 6 | AArch64 enforcement | 1816 AArch64, 0 userspace-32 |
| 7 | 0-byte blob scan | **32 found** (pre-existing, needs re-extraction) |
| 8 | PRODUCT_COPY_FILES resolution | 3153/3153 resolve |
| 9 | Generated-file drift | in sync |
| 10 | Exec bits | 4 scripts were missing `+x` — fixed |
| 11 | Doc links | 0 broken |
| 12 | Scripts referenced in docs | all exist |
| 13 | Test-count claim vs reality | matches (46) |
| 14 | Symlink targets | 0 broken relative links |
| 15 | Blob coverage | 3153 on disk, 3153 referenced, 0 orphans |
| 16 | Board vs Product variable placement | **1 bug** (see below) |
| 17 | Android.bp namespace list | 18 imports, all CAF paths |
| 18 | Duplicate copy destinations | 0 (no silent overwrites) |
| 19 | modules.load vs `.ko` on disk | 278/281, duplicates only |
| 20 | README claims vs real files | Vulkan 1.3, 27 QNN libs, Adreno stack all verified |

#### Fixed in this round

| Severity | Bug | Fix |
|---|---|---|
| Medium | `PRODUCT_SHIPPING_API_LEVEL := 36` was set in `BoardConfigVendor.mk`. It is a **product** variable; board config is parsed by the board reader, so the assignment was inert. | Moved to `vendor-port.mk` (the product-side entry point). |
| Medium | `Android.mk` used `include $(BUILD_PHONY_PACKAGE)`. That is a legacy/CAF macro base AOSP does not define — on a plain AOSP tree the include expanded to nothing. | Guarded with `ifeq`; falls back to a real `.PHONY` target when undefined. |
| Low | `check_arch.py` never checked for x86/x86-64, despite "no x86 stuff" being an explicit goal. | Added `FOREIGN_MACHINES` detection, with a synthetic x86-64 fixture proving it fires. |
| Low | 4 scripts shipped without the executable bit. | `chmod +x`. |
| Low | 16 `A && B || C` patterns in the test suite: the "fail" branch can run after a *success* if the success handler exits non-zero, masking a real failure. | Rewritten as `if … then … else … fi`. |
| Low | Ruff: unused import, unused local, 3 placeholder-free f-strings, 2 unchecked `subprocess.run`. | Fixed. |

#### Verified, not assumed

Claims in this README were checked against the actual blobs rather than
trusted:

- Vulkan 1.3 — `android.hardware.vulkan.version-1_3.xml` present
- QNN — **27** `libQnn*.so` libraries present, incl. `libSnpeDspV65Stub.so`
- Adreno stack — all 5 named libraries present (`vulkan.adreno.so`, …)
- Test count — 46, matching the claim in this file

---

## Verification & Self-Test Suite

This repository includes a test suite verifying super image unpacking, EROFS parsing, fixture validation, makefile generation, 64-bit integrity, and service sanity:

```bash
./scripts/tests/run-tests.sh
```

```text
fixture generation ........................... PASS
independent oracle (upstream lpunpack) ....... PASS
extractor matches oracle byte-for-byte ....... PASS
sparse image decompression ................... PASS
slot-suffixed metadata ....................... PASS
missing partitions warned, not fatal ......... PASS
manifest structure ........................... PASS
integrity checks & checksum handling ......... PASS
generated vendor.mk is valid GNU make ........ PASS
no dangling continuation ..................... PASS
short write leaves no truncated image ........ PASS
bad output paths give clean errors ........... PASS
every PRODUCT_COPY_FILES source resolves ..... PASS
device-absolute symlinks kept ................ PASS
empty critical blobs reported ................ PASS
userspace is 100% AArch64 .................... PASS
coprocessor firmware preserved ............... PASS
no 32-bit ABI advertised ..................... PASS
build files in sync with targets.json ........ PASS
ruan / garnet / organ / flute resolve ........ PASS
unsupported device skipped cleanly ........... PASS
kernel modules resolve & match modules.load .. PASS
-----------------------------------------------
Result: 46 passed, 0 failed
```

---

## Credits & Acknowledgements

- **[Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip)**: Primary Linux 6.6.162 GKI kernel tree for `ruan`.
- **Qualcomm Technologies, Inc. & Code Aurora Forum**: Open-source HALs, kernel headers, and platform architecture.
- **LineageOS & TheMuppets**: Hardware compatibility references for SM7435 sister platforms.
- **Xiaomi**: Original stock OS3.0.306.0.WFSINXM firmware images.
