#
# Copyright (c) 2026 Nordic Semiconductor
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
#
# Wi-Fi LMAC/UMAC ROM patch DFU support for nRF7120.
#
# Design
# ======
# The LMAC/UMAC patch binaries are GPL-licensed and position-dependent:
# they contain absolute ARM MRAM address references and MUST reside at
# exactly the addresses declared in manifest.json (lmac_origin/umac_origin).
#
# Two manifest variants are shipped by the Wi-Fi team:
#   non-TFM/manifest.json  — origins in the slot0   partition (cpuapp)
#   tfm/manifest.json      — origins in the slot0_ns partition (cpuapp_ns)
#
# Linker guard
# ------------
# A linker section is placed at each declared origin.  If app code or data
# ever grows into the patch area the linker emits a section overlap error at
# build time — no silent corruption at runtime.
#
# FOTA correctness
# ----------------
# inject_wifi_patch.py writes the actual patch bytes into the zero
# reservations in zephyr.bin BEFORE imgtool signs the image.  Therefore
# zephyr.signed.bin includes the patches at the correct binary offsets.
# When MCUboot performs a slot1 -> slot0 swap the patches land at exactly
# lmac_origin / umac_origin in MRAM.
#
# No imgtool change needed: patch origins are ~960 KB into slot0, far beyond
# the MCUboot header zone (bytes 0..ROM_START_OFFSET-1) that check_header()
# inspects.
#
# Build artifacts
# ---------------
#   zephyr.signed.bin   — MCUboot-signed image for app+patch FOTA
#   zephyr.hex          — combined factory programming image

if(NOT CONFIG_WIFI_NRF71_PATCH)
  return()
endif()

# ---------------------------------------------------------------------------
# Locate firmware directory and manifest
# ---------------------------------------------------------------------------
set(_fw_base "${ZEPHYR_NRFXLIB_MODULE_DIR}/nrf_wifi/bin/nrf7120")
set(_fw_dir  "${_fw_base}/${CONFIG_WIFI_NRF71_PATCH_VERSION}")

if(NOT IS_DIRECTORY "${_fw_dir}")
  message(FATAL_ERROR
    "nRF7120 Wi-Fi patch version not found: ${_fw_dir}\n"
    "Set CONFIG_WIFI_NRF71_PATCH_VERSION to an existing directory under "
    "${_fw_base}/.")
endif()

set(_manifest_file "${_fw_dir}/manifest.json")
if(NOT EXISTS "${_manifest_file}")
  message(FATAL_ERROR "Missing nRF7120 Wi-Fi patch manifest: ${_manifest_file}")
endif()

file(READ "${_manifest_file}" _manifest)

# ---------------------------------------------------------------------------
# Parse manifest — file names, fixed MRAM origins, and patch sizes.
# The origins are declared by the Wi-Fi team; they are not computed here.
# ---------------------------------------------------------------------------
set(_has_lmac FALSE)
set(_has_umac FALSE)

string(JSON _lmac_file   ERROR_VARIABLE _err  GET "${_manifest}" lmac_patch)
string(JSON _lmac_origin ERROR_VARIABLE _err2 GET "${_manifest}" lmac_origin)
if(NOT _err AND NOT _err2)
  set(_lmac_bin "${_fw_dir}/${_lmac_file}")
  if(NOT EXISTS "${_lmac_bin}")
    message(FATAL_ERROR "Manifest lmac_patch='${_lmac_file}' not found: ${_lmac_bin}")
  endif()
  math(EXPR _lmac_addr "${_lmac_origin}")   # hex string -> decimal for C macro
  file(SIZE "${_lmac_bin}" _lmac_size)
  string(JSON _lmac_sz ERROR_VARIABLE _err GET "${_manifest}" lmac_size)
  if(NOT _err AND NOT "${_lmac_sz}" STREQUAL "${_lmac_size}")
    message(FATAL_ERROR
      "Manifest lmac_size=${_lmac_sz} does not match actual file size "
      "${_lmac_size} B: ${_lmac_bin}")
  endif()
  set(_has_lmac TRUE)
endif()

string(JSON _umac_file   ERROR_VARIABLE _err  GET "${_manifest}" umac_patch)
string(JSON _umac_origin ERROR_VARIABLE _err2 GET "${_manifest}" umac_origin)
if(NOT _err AND NOT _err2)
  set(_umac_bin "${_fw_dir}/${_umac_file}")
  if(NOT EXISTS "${_umac_bin}")
    message(FATAL_ERROR "Manifest umac_patch='${_umac_file}' not found: ${_umac_bin}")
  endif()
  math(EXPR _umac_addr "${_umac_origin}")
  file(SIZE "${_umac_bin}" _umac_size)
  string(JSON _umac_sz ERROR_VARIABLE _err GET "${_manifest}" umac_size)
  if(NOT _err AND NOT "${_umac_sz}" STREQUAL "${_umac_size}")
    message(FATAL_ERROR
      "Manifest umac_size=${_umac_sz} does not match actual file size "
      "${_umac_size} B: ${_umac_bin}")
  endif()
  set(_has_umac TRUE)
endif()

if(NOT _has_lmac AND NOT _has_umac)
  message(FATAL_ERROR
    "Manifest must declare lmac_patch+lmac_origin and/or "
    "umac_patch+umac_origin: ${_manifest_file}")
endif()

message(STATUS "nRF7120 Wi-Fi ROM patches:")
if(_has_lmac)
  message(STATUS "  LMAC: ${_lmac_size} B at MRAM ${_lmac_origin}  ${_lmac_bin}")
endif()
if(_has_umac)
  message(STATUS "  UMAC: ${_umac_size} B at MRAM ${_umac_origin}  ${_umac_bin}")
endif()

# ---------------------------------------------------------------------------
# Linker sections — reserve space at exact MRAM origins.
# Provides build-time overlap detection: linker errors if app code/data
# encroaches on the reserved patch addresses.
# ---------------------------------------------------------------------------
if(_has_lmac)
  set(section_name wifi_lmac_patch)
  set(patch_origin ${_lmac_addr})
  set(patch_size   ${_lmac_size})
  configure_file(
    "${CMAKE_CURRENT_LIST_DIR}/wifi_patch_section.ld.in"
    "${CMAKE_CURRENT_BINARY_DIR}/wifi_lmac_section.ld"
    @ONLY)
  zephyr_linker_sources(SECTIONS "${CMAKE_CURRENT_BINARY_DIR}/wifi_lmac_section.ld")
endif()

if(_has_umac)
  set(section_name wifi_umac_patch)
  set(patch_origin ${_umac_addr})
  set(patch_size   ${_umac_size})
  configure_file(
    "${CMAKE_CURRENT_LIST_DIR}/wifi_patch_section.ld.in"
    "${CMAKE_CURRENT_BINARY_DIR}/wifi_umac_section.ld"
    @ONLY)
  zephyr_linker_sources(SECTIONS "${CMAKE_CURRENT_BINARY_DIR}/wifi_umac_section.ld")
endif()

# ---------------------------------------------------------------------------
# Compile-time address constants consumed by wifi_patch_addrs.c.
# NRF7120_WIFI_{LMAC,UMAC}_PATCH_ADDR are C preprocessor macros — uppercase.
# ---------------------------------------------------------------------------
zephyr_library()
zephyr_library_sources(wifi_patch_addrs.c)
if(_has_lmac)
  zephyr_library_compile_definitions(NRF7120_WIFI_LMAC_PATCH_ADDR=${_lmac_addr}U)
endif()
if(_has_umac)
  zephyr_library_compile_definitions(NRF7120_WIFI_UMAC_PATCH_ADDR=${_umac_addr}U)
endif()

# ---------------------------------------------------------------------------
# Post-link injection — fills zero reservations with actual patch bytes.
#
# inject_wifi_patch.py targets BOTH:
#   zephyr.bin  — so imgtool signs the complete binary (app + patches);
#                 zephyr.signed.bin is the FOTA image used by MCUboot
#   zephyr.hex  — combined factory programming image
#
# Ordering: APPEND runs before zephyr_mcuboot_tasks() appends the imgtool
# sign commands, so injection always precedes signing.
# ---------------------------------------------------------------------------
dt_nodelabel(_slot0_node NODELABEL "slot0_partition" REQUIRED)
dt_reg_addr(_code_base PATH "${_slot0_node}")

set(_inject_cmd
  COMMAND "${PYTHON_EXECUTABLE}"
    "${CMAKE_CURRENT_LIST_DIR}/inject_wifi_patch.py"
    --app-bin   "${APPLICATION_BINARY_DIR}/zephyr/zephyr.bin"
    --app-hex   "${APPLICATION_BINARY_DIR}/zephyr/zephyr.hex"
    --code-base "${_code_base}"
)
if(_has_lmac)
  list(APPEND _inject_cmd
    --lmac-bin    "${_lmac_bin}"
    --lmac-origin "${_lmac_origin}"
  )
endif()
if(_has_umac)
  list(APPEND _inject_cmd
    --umac-bin    "${_umac_bin}"
    --umac-origin "${_umac_origin}"
  )
endif()

set_property(GLOBAL APPEND PROPERTY extra_post_build_commands ${_inject_cmd})
