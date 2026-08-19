# Iterative Design and the Future of Flyber

This project defines an evidence-based iterative design program for Flyber after its initial New York City launch. It combines product KPIs, multivariate-experiment evaluation, event-log funnel and cohort analysis, qualitative rider research, and a proposed next experiment to identify the most promising path forward.

## Measurement framework

The north-star metric is **ride-launch conversion per opened session**: sessions that begin a ride divided by opened sessions. Supporting metrics include search completion and ride frequency. Revenue, margin, retention, and safety outcomes are important future KPIs but require additional fare, cost, cohort, cancellation, and incident data.

## Prior multivariate experiment

The prior 2×2 test varied call-to-action wording and price transparency. Experiment 2 produced the highest observed conversion rate (0.318% versus 0.273% for control), but the lift was small and statistically uncertain. Welch two-sample t-tests with Holm adjustment found no statistically significant difference from control (adjusted p-values: 0.506–0.636). The recommendation is to retain control and rerun a preregistered, user-randomized experiment rather than expand any existing variant.

## Funnel, cohorts, and next steps

The analysis evaluates the strictly ordered funnel from session open through rider-count selection and trip search to a ride launch. Only 0.30% of opened sessions launch a ride; the largest relative loss occurs between search and ride launch. Age-based cohort analysis identifies underperforming segments, and rider interviews supply qualitative evidence for hypotheses about unmet needs. The proposed next test targets the affected cohort, compares multiple feature alternatives, predicts impact from the observed gap, and expands the measurement plan with additional decision metrics.

## Included analysis assets

The `tableau/` folder contains the supporting workbook and exported experiment, funnel, and age-cohort visuals. Local event logs and interview data are deliberately excluded from the public repository.

## Final presentation

Select an image to view it at full size.

[![Slide 1](readme-assets/slide-01.png)](readme-assets/slide-01.png)
[![Slide 2](readme-assets/slide-02.png)](readme-assets/slide-02.png)
[![Slide 3](readme-assets/slide-03.png)](readme-assets/slide-03.png)
[![Slide 4](readme-assets/slide-04.png)](readme-assets/slide-04.png)
[![Slide 5](readme-assets/slide-05.png)](readme-assets/slide-05.png)
[![Slide 6](readme-assets/slide-06.png)](readme-assets/slide-06.png)
[![Slide 7](readme-assets/slide-07.png)](readme-assets/slide-07.png)
[![Slide 8](readme-assets/slide-08.png)](readme-assets/slide-08.png)
[![Slide 9](readme-assets/slide-09.png)](readme-assets/slide-09.png)
[![Slide 10](readme-assets/slide-10.png)](readme-assets/slide-10.png)
[![Slide 11](readme-assets/slide-11.png)](readme-assets/slide-11.png)
[![Slide 12](readme-assets/slide-12.png)](readme-assets/slide-12.png)
[![Slide 13](readme-assets/slide-13.png)](readme-assets/slide-13.png)
[![Slide 14](readme-assets/slide-14.png)](readme-assets/slide-14.png)
[![Slide 15](readme-assets/slide-15.png)](readme-assets/slide-15.png)
[![Slide 16](readme-assets/slide-16.png)](readme-assets/slide-16.png)
[![Slide 17](readme-assets/slide-17.png)](readme-assets/slide-17.png)
[![Slide 18](readme-assets/slide-18.png)](readme-assets/slide-18.png)
[![Slide 19](readme-assets/slide-19.png)](readme-assets/slide-19.png)
[![Slide 20](readme-assets/slide-20.png)](readme-assets/slide-20.png)
[![Slide 21](readme-assets/slide-21.png)](readme-assets/slide-21.png)
[![Slide 22](readme-assets/slide-22.png)](readme-assets/slide-22.png)
[![Slide 23](readme-assets/slide-23.png)](readme-assets/slide-23.png)
[![Slide 24](readme-assets/slide-24.png)](readme-assets/slide-24.png)
[![Slide 25](readme-assets/slide-25.png)](readme-assets/slide-25.png)
[![Slide 26](readme-assets/slide-26.png)](readme-assets/slide-26.png)
[![Slide 27](readme-assets/slide-27.png)](readme-assets/slide-27.png)

## Files

- [Iterative design presentation (PDF)](Ohara-Flyber_Iterative_Design.pdf)
- [Tableau analysis assets](tableau/)
