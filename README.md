# Code Appendix: FREYA - Bachelor thesis

This repository contains the source code developed as part of the bachelor's thesis *"[Title]"* at The Norwegian Cyber Defense University College, submitted May 2026. The thesis was made in collaboration with NORCE Research and Meteomatics.

## Authors

- Nils Christian Wikstrøm – api-client, docs
- Stian Sivertsen Loddengaard – diode-rx, diode-tx, docs
- Ina Utne Skogdalen

## About the project

The system retrieves meteorological data from an external API, transmits it over a one-way data diode, and processes the received data on the receiving side for use in artillery fire control.

For a full description of the system architecture, design choices, and results, see chapters 5 and 6 of the thesis.

## Repository structure

| Directory     | Contents                                                    |
|---------------|-------------------------------------------------------------|
| `api-client/` | Retrieval and processing of weather data from external API  |
| `diode-tx/`   | Transmitter side: packaging and transmission over diode     |
| `diode-rx/`   | Receiver side: reception, validation, and storage           |
| `docs/`       | Test matrixes for the project                               |

## Dependencies

**Python:** version 3.11 or newer, and the following packages:

```
requests mgrs
```

Install required packages with:

```
pip install -r requirements.txt
```

**PowerShell:** version 5.1 or 7.x. Some scripts may require setting the execution policy:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Citing this code

The version submitted with the thesis is tagged `v1.0-submission` (commit `[hash inserted at submission]`).

When referencing this code, please cite the thesis itself; this repository serves as the accompanying code appendix.

## License

See `LICENSE`. This code is **not** released under an open-source license; reuse requires written permission from the authors.

## Disclaimer

This source code was developed as part of academic work and is not intended for operational use without further validation, testing, and security review.
