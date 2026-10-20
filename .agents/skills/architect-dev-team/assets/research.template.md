# Research: <task_id> — <role>

**Question**: <precise question>
**Architecture Version**: <arch version>
**Milestone**: <milestone ID>
**Date**: <ISO8601>
**Specialist**: <role name>

---

## Sources Consulted

| Source | Type | Version/Date | URL/Reference | Credibility |
|--------|------|--------------|---------------|-------------|
| <name> | <official doc / standard / paper / spec> | <version> | <URL> | <high/medium/low> |

---

## Findings

### Specifications / Formulas / Algorithms
<Detailed technical specifications, mathematical formulas, algorithm descriptions, pseudocode>

### Units & Measurements
| Quantity | Unit | System | Notes |
|----------|------|--------|-------|
| <name> | <SI/domain> | <metric/imperial/custom> | <conversion if needed> |

### Tolerances & Precision
| Parameter | Required Precision | Acceptable Range | Basis |
|-----------|-------------------|------------------|-------|
| <name> | <e.g., 1e-6> | <min–max> | <standard / empirical / derived> |

### Reference Values (Known Good Results)
| Test Case | Expected Result | Source |
|-----------|-----------------|--------|
| <input> | <output> | <reference> |

### Invariants (Must-Hold Properties)
- <property 1>
- <property 2>

---

## Assumptions (Reversible Defaults)

| Assumption | Source | Reversible? | Impact if Wrong |
|------------|--------|-------------|-----------------|
| <assumption> | <source> | Yes/No | <description> |

---

## Conflicting Evidence

| Finding A | Source A | Finding B | Source B | Resolution |
|-----------|----------|-----------|----------|------------|
| <claim> | <ref> | <contrary claim> | <ref> | <lead decision or open> |

---

## Applicability Limits

- <constraint 1: e.g., "Valid for temperatures 0–100°C only">
- <constraint 2: e.g., "Assumes IEEE 754 double precision">

---

## Architecture Recommendation

<Concrete recommendation for architecture: component design, interface contract, algorithm choice, validation approach>

**Confidence**: High / Medium / Low
**Blocking Decisions**: <any open decisions needing human input>