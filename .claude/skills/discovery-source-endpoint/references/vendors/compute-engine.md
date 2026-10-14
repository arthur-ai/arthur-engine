# Compute Engine (cloud-host carrier)

| Requirement | Compute Engine |
|---|---|
| Run a script as root on a schedule | OS policy + systemd timer |
| Per-device string attribute | guest attribute (cap 262,144 bytes) |
| Inventory API by report date | none: enumerate fully every run, and say so in the docs |
| Stable device id | the instance's numeric `id` |

Connection takes the project and a service credential, as a cloud source does, instead of `base_url`.
