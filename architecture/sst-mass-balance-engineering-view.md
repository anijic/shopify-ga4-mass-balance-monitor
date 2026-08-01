# SST + Mass Balance – Engineering View

```mermaid
graph LR
  classDef client fill:#e1f5fe,stroke:#3b82f6,stroke-width:2px,color:#000
  classDef proxy fill:#e8f5e9,stroke:#10b981,stroke-width:2px,color:#000
  classDef data fill:#fff3e0,stroke:#f59e0b,stroke-width:2px,color:#000
  classDef control fill:#f3e8ff,stroke:#8b5cf6,stroke-width:2px,color:#000

  subgraph Client["Client Edge"]
    A[User Browser]:::client
    B[GTM Web Container<br/>GTM-TTZ2JRGD]:::client
    A --> B
  end

  subgraph UnitOps["Unit Ops – Measurement & Truth"]
    C[Client-Side Measurement Layer]:::proxy
    D[Shopify Truth Layer<br/>shopify_orders_setpoint.csv<br/>generate_shopify_setpoint.py]:::proxy
  end

  subgraph Reactor["Reactor – SST Proxy & Join Engine"]
    E[collect.aniji.ca → App Engine<br/>sst-portfolio-aniji · nodejs20]:::proxy
    F[GTM Server Container<br/>GTM-P5CT43RR<br/>Server Managed FPID]:::proxy
    G[(BigQuery Intraday Export<br/>analytics_542298950.events_*)]:::data
    H[(GA4 Reactor Table<br/>ga4_purchases_jan2021)]:::data
    I[(Mass Balance Reactor<br/>ga4_shopify_mass_balance_jan2021)]:::data
  end

  subgraph ControlPanel["Control Panel – FMEA & Dashboard"]
    J[(vw_mass_balance_reconciliation)]:::control
    K[(vw_channel_attribution_health)]:::control
    L[Looker Studio Dashboard<br/>Phantom ROAS Leak Detection]:::control
  end

  B --> C
  C --> E
  E --> F
  F --> G
  D --> I
  G --> H
  H --> I
  I --> J
  J --> K
  K --> L
```
