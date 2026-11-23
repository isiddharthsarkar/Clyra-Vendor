# Clyra-Vendor — Redmi Pad Pro 5G (`ruan`)

Proprietary vendor blobs and open-source HAL definitions for **Redmi Pad Pro 5G (`ruan`)** — Qualcomm SM7435 (`parrot`).

| Metadata | Value |
|---|---|
| Device | Redmi Pad Pro 5G (`24074RPD2G`) |
| Codename | `ruan` |
| Platform | Qualcomm SM7435 (`parrot` / Snapdragon 7s Gen 2) |
| Region | India (`in`) |
| Official ROM | `ruan_in_global_images_OS3.0.306.0.WFSINXM_20261021.0000.00_16.0_in_e97cbecd4c.tgz` |
| Vendor Base | Android 12L (SDK 32 / `SKQ1.231214.001`) |
| Kernel Support | [Clyra-Flip](https://github.com/isiddharthsarkar/Clyra-Flip) (Linux 6.6 / GKI 3.1 / Android 16) |

---

## Clyra-Flip Kernel Integration

This vendor tree is configured to directly support the [Clyra-Flip Kernel](https://github.com/isiddharthsarkar/Clyra-Flip):
- **Architecture**: `arm64`
- **GKI Version**: `3.1` (Android 16 / Linux 6.6)
- **Defconfig Chain**:
  ```text
  gki_defconfig vendor/parrot_GKI.config vendor/ruan_GKI.config vendor/ruan_android16.config
  ```
- **Modules (`vendor_dlkm`)**: Stock modules and load orders are mapped in `proprietary/vendor_dlkm/lib/modules/` and dynamically loadable via GKI KMI compatibility.

---

## Open Source Software (OSS) HAL Support

Configured for AOSP / LineageOS / Custom ROM builds with Soong namespaces:
- `hardware/xiaomi`
- `hardware/qcom-caf/sm8450`
- `vendor/qcom/opensource/commonsys-intf/display`
- `vendor/qcom/opensource/audio-hal/primary-hal`
- `vendor/qcom/opensource/data-ipa-cfg-mgr`

---

## Repository Layout

```text
├── Android.bp                  # Soong namespace and prebuilt library rules
├── BoardConfigVendor.mk        # Platform, architecture, kernel and OSS definitions
├── vendor.mk                   # Complete PRODUCT_COPY_FILES mappings
├── proprietary/                # Extracted proprietary blobs
│   ├── odm/
│   ├── vendor/
│   └── vendor_dlkm/
├── scripts/                    # ROM download & extraction pipeline
├── firmware/                   # Firmware profiles and partition lists
└── .github/                    # CI verification workflows
```
