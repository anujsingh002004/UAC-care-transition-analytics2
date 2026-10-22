# 🛡️ UAC Care Transition Efficiency Analytics

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-5.18%2B-orange.svg)](https://plotly.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Reframing child welfare monitoring from static custody headcounts to dynamic process velocity, queue theory, and bottleneck identification.**

---

## 📌 1. Background & Problem Statement

The **Unaccompanied Alien Children (UAC) Program** functions as a multi-stage care and reunification pipeline rather than a static holding system. 

```mermaid
flowchart LR
    A["Intake\n(Apprehensions)"] --> B["Stage 1: CBP Custody\n(Active CBP Load)"]
    B -->|Transfer Out| C["Stage 2: HHS Care\n(Active Shelter Load)"]
    C -->|Discharge / Reunification| D["Stage 3: Sponsor Placement\n(Exit)"]
    
    subgraph Bottlenecks["Critical Bottleneck Zones"]
        B -.->|"Transfer Delays"| B
        C -.->|"Case Vetting Backlog"| C
    end
