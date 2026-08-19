# Flyber Data Strategy MVP

This project develops an end-to-end data strategy for Flyber, a two-sided transportation platform experiencing rapid growth in rider activity and application telemetry. The work begins with stakeholder and data-requirement analysis, converts raw rider event logs into validated daily summaries, analyzes one month of event growth, and concludes with a cloud data warehouse recommendation.

The project is structured as an MVP. The objective is not only to produce descriptive statistics, but also to define the data model, transformation logic, validation controls, and infrastructure decisions required to make the analysis repeatable at production scale.

## 1. Project Objectives

The project addresses five related questions:

1. Who are Flyber's primary internal data stakeholders, and which decisions require data?
2. Which data fields and normalized tables are required for the rider-side MVP?
3. How can the supplied raw event logs be extracted, transformed, aggregated, and validated?
4. What does the available data indicate about event growth, campaign effects, and operational scale?
5. Which data warehouse architecture is appropriate for Flyber's current growth trajectory?

## 2. Deliverables

The public portfolio contains the following primary artifacts:

- `flyber-data-strategy-proposal-completed.pdf`: Completed proposal containing stakeholder analysis, data requirements, relational data models, ETL documentation, visualizations, business analysis, and the data warehouse recommendation.
- `section-3-event-logs-completed.xlsx`: Original event-log workbook with 124,980 raw events and a completed `ETL` worksheet containing the five required daily aggregations.
- `section-5-data-completed.xlsx`: One-month event-type dataset with a formula-driven analysis worksheet and continuous line visualizations.
- `python-source/`: Reproducible extraction, analysis, visualization, workbook-construction, and proposal-population scripts.

## 3. Source Data

### Section 3 event logs

The raw event dataset contains 124,980 observations with the following fields:

- `event_uuid`
- `user_uuid`
- `event_time`
- `device_type`
- `session_uuid`
- `user_neighborhood`
- `event_page`
- `event_type`

The complete reporting window is October 5 through October 11, 2019. The source also contains an incomplete October 12 boundary segment. That segment is excluded from the daily ETL summaries because treating a partial day as a complete day would create a false decline.

### Section 5 event-type data

The Section 5 dataset contains daily event totals from September 11 through October 11, 2019 for:

- Choose Car
- Search
- Open
- Begin Ride
- Request Car
- Total Event

## 4. Methodology

### 4.1 Stakeholder and requirements analysis

Four primary stakeholder groups were selected across separate business functions:

- Engineering / Platform
- Product Management
- Marketing / Growth
- Finance / Operations

Each stakeholder is linked to one or two primary use cases, required MVP fields, and a rationale explaining why the data is needed. This keeps the collection strategy traceable to a concrete decision rather than treating data collection as an independent objective.

### 4.2 Relational data model

The rider-side MVP uses three normalized tables:

1. `Rider`
2. `Session`
3. `Event`

The model establishes one-to-many relationships from Rider to Session and from Session to Event. Stable identifiers are used as primary keys, while foreign keys preserve rider journeys without repeating rider attributes in every event record.

### 4.3 ETL process

The ETL process follows five stages:

1. Extract the supplied workbook while preserving UUIDs and timestamp values.
2. Standardize timestamps and categorical labels.
3. Filter the analysis to complete calendar days.
4. Aggregate event counts by date, event type, device type, page type, and location.
5. Reconcile every categorical subtotal to the corresponding daily event total.

The completed ETL worksheet includes visible reconciliation checks. All four categorical summaries reconcile for all seven reporting days.

### 4.4 Data visualization and analysis

Continuous line visualizations were created for Choose Car and Begin Ride activity. Additional graphs show total event growth and all event types on a logarithmic scale. The logarithmic view is important because Begin Ride activity is several orders of magnitude smaller than Open activity, but the two series still share a comparable temporal pattern.

The campaign window is defined as October 1 through October 7. Campaign-period averages are compared with the immediately preceding seven-day period. This is an observational comparison rather than a causal estimate because no randomized control group or counterfactual series is available.

### 4.5 Infrastructure analysis

The warehouse decision evaluates:

- Cost
- Scalability
- Required expertise
- Latency and connectivity
- Reliability

Google BigQuery is recommended as the initial cloud data warehouse. The recommendation is based on serverless scaling, separation of storage and compute, standard SQL access, managed reliability, and the ability to partition and cluster rapidly growing event tables.

## 5. Technologies

- Microsoft Excel / Office Open XML for source data, ETL summaries, formulas, and workbook visualizations
- Microsoft Word for the proposal deliverable
- Python 3 for extraction, aggregation, validation, and reproducibility checks
- Matplotlib for publication-ready time-series visualizations
- LibreOffice for independent workbook compatibility and round-trip verification
- ZIP for the final submission package

## 6. Key Results

- Total daily event volume increased from 790,329 to 12,788,264 events in one month.
- The endpoint daily run rate increased by 16.18x, or 1,518.1%.
- Daily volume peaked at 18,918,096 events on October 4, 2019.
- Choose Car showed the fastest endpoint growth at 30.54x.
- Average campaign-period volume was 14.22 million events per day.
- Campaign-period volume was 211.6% higher than the September 24-30 comparison period.
- All five event types followed a common growth, campaign-peak, decline, and stabilization pattern.

## 7. Project Structure

```text
scalable-data-strategy/
|-- README.md
|-- flyber-data-strategy-proposal-completed.pdf
|-- section-3-event-logs-completed.xlsx
|-- section-5-data-completed.xlsx
|-- python-source/
`-- readme-assets/
```

## 8. Verification and Validation

Verification asks whether the deliverables were constructed correctly. Validation asks whether the deliverables answer the business and rubric requirements.

The following checks were completed:

- Confirmed 124,980 raw event records plus one header row in the Section 3 workbook.
- Confirmed both the raw-log and ETL worksheets are present.
- Confirmed ETL counts are numeric and use count formatting rather than date formatting.
- Reconciled event-type, device-type, page-type, and location subtotals to daily totals.
- Confirmed all four ETL reconciliation controls return `PASS`.
- Confirmed the Section 5 workbook contains the source and analysis worksheets and at least two continuous line charts.
- Confirmed proposal placeholders were removed.
- Confirmed the proposal contains the required growth multiple, peak, campaign comparison, and warehouse factors.
- Reopened and round-tripped the final Section 3 workbook through an independent spreadsheet application.
- Tested the final ZIP archive and verified that the packaged Section 3 workbook matches the independently validated file.

Editable Word source remains local-only; the completed PDF is the portable public proposal.

## 9. Assumptions and Limitations

- The October 12 event-log segment is incomplete and is therefore excluded from the seven-day ETL window.
- Event activity can indicate customer engagement, but it cannot determine exact unique-customer growth without a rider or account-creation dataset.
- Request Car and Begin Ride are used as transactional proxies. Exact financial transaction growth requires a dedicated ride or transaction table.
- The October campaign coincides with the observed event spike, but the available observational data does not establish causality.
- Visualizations were created with Python, which is explicitly permitted by the project instructions as an alternative to Tableau. A public Tableau dashboard link is an optional enhancement and is not claimed as a deliverable.

## 10. Recommended Next Steps

1. Automate incremental ingestion from immutable cloud object storage.
2. Add schema validation, deduplication on `event_id`, null checks, and quarantine handling.
3. Implement Rider, Session, Event, and Ride warehouse models with documented grain and ownership.
4. Partition event facts by event date and cluster on frequently filtered identifiers.
5. Add campaign exposure and acquisition-channel data to support causal or quasi-experimental analysis.
6. Establish freshness, completeness, latency, and reconciliation service-level indicators.

## Visual archive

Select an image to view it at full size.

[![Proposal page 1](readme-assets/page-01.png)](readme-assets/page-01.png)
[![Proposal page 2](readme-assets/page-02.png)](readme-assets/page-02.png)
[![Proposal page 3](readme-assets/page-03.png)](readme-assets/page-03.png)
[![Proposal page 4](readme-assets/page-04.png)](readme-assets/page-04.png)
[![Proposal page 5](readme-assets/page-05.png)](readme-assets/page-05.png)
[![Proposal page 6](readme-assets/page-06.png)](readme-assets/page-06.png)
[![Proposal page 7](readme-assets/page-07.png)](readme-assets/page-07.png)
[![Proposal page 8](readme-assets/page-08.png)](readme-assets/page-08.png)
[![Proposal page 9](readme-assets/page-09.png)](readme-assets/page-09.png)
[![Proposal page 10](readme-assets/page-10.png)](readme-assets/page-10.png)
[![Proposal page 11](readme-assets/page-11.png)](readme-assets/page-11.png)
[![Proposal page 12](readme-assets/page-12.png)](readme-assets/page-12.png)
[![Proposal page 13](readme-assets/page-13.png)](readme-assets/page-13.png)
[![Proposal page 14](readme-assets/page-14.png)](readme-assets/page-14.png)
[![Proposal page 15](readme-assets/page-15.png)](readme-assets/page-15.png)
[![Proposal page 16](readme-assets/page-16.png)](readme-assets/page-16.png)
[![Proposal page 17](readme-assets/page-17.png)](readme-assets/page-17.png)

## Files

- [Completed data strategy proposal (PDF)](flyber-data-strategy-proposal-completed.pdf)
- [Event-log ETL workbook](section-3-event-logs-completed.xlsx)
- [Event-growth analysis workbook](section-5-data-completed.xlsx)
- [Reproducible Python source](python-source/)
