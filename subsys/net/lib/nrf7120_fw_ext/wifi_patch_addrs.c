/*
 * Copyright (c) 2026 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 *
 * Strong overrides of the __weak soc_nrf71_wifi_{lmac,umac}_patch_addr()
 * stubs from the SoC tree.
 *
 * The addresses are compile-time constants derived from lmac_origin /
 * umac_origin in manifest.json and injected as preprocessor defines by
 * CMakeLists.txt.  The patch binaries are position-dependent (non-PIC,
 * absolute ARM MRAM address references) and MUST be placed at exactly these
 * addresses.  They reside in a dedicated MRAM partition that is completely
 * outside the MCUboot-managed slot0/slot1 — no linker conflict is possible.
 */

#include <stdint.h>

#ifdef NRF7120_WIFI_LMAC_PATCH_ADDR
uint32_t soc_nrf71_wifi_lmac_patch_addr(void)
{
	return NRF7120_WIFI_LMAC_PATCH_ADDR;
}
#endif

#ifdef NRF7120_WIFI_UMAC_PATCH_ADDR
uint32_t soc_nrf71_wifi_umac_patch_addr(void)
{
	return NRF7120_WIFI_UMAC_PATCH_ADDR;
}
#endif
