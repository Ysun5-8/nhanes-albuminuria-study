# Input integrity

SHA-256 values for the cached public NHANES XPT files used in the analysis:

| File | SHA-256 |
|---|---|
| `ALB_CR_L.xpt` | `fc011a80d14419884559372a3196f0a268b494f4f2fa972d00be1f3a23ba3c41` |
| `DEMO_L.xpt` | `ca4374a158b493b8b0163e1388da21d57a18d1b9cecff2aa4e2fa2bec494fe23` |
| `P_ALB_CR.xpt` | `c493f6b74cc0608bb7083b92e074fc3070b9e614fd5e1e34d0ce943e0f6116bf` |
| `P_DEMO.xpt` | `2e46c6c26bf77cd8989f64011ace12cbf42c0f3e03414eb59acc5328c8f87913` |

The raw files are excluded from Git. These hashes identify the cached inputs;
they are not a guarantee that CDC will never revise a download. Input acquisition
and verification commands are documented in [reproduction.md](reproduction.md).
