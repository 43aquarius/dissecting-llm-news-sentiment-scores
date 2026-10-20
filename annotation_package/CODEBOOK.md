# Codebook: Classifying Realized-Price ("Echo") Headlines

Four mutually exclusive categories. Apply the steps in order; the first step
that applies determines the label.

## Categories

**P -- Realized price move.** The headline states or clearly implies that the
company's stock price has ALREADY moved. Markers: past or present-perfect tense
("dropped 5% after earnings", "soars after results", "has gained 5% so far"),
performance summaries ("second-best day ever"), technical levels ("falls below
its 200-day moving average"). Includes realized moves stated together with a
fundamental cause ("shares jump on blowout results" -- the move is reported).

**E -- Fundamental magnitude.** The matched keyword describes a FUNDAMENTAL
result or event magnitude, not the stock: "revenue rises 12%" (the rise is the
revenue's), "sales jump 20%", expected quarterly results ("FQ1 gains" expected
from earnings), analyst catalyst actions. No realized stock-price move is stated.

**D -- Directional forecast.** The keyword is a forecast or expectation of
FUTURE stock direction: "could sink in 2026", "may drop to $300", "can it
bounce back?", price-target chatter without a realized move.

**N -- Regex false positive.** The keyword is incidental with no stock-price
meaning: "execution short fall" (shortfall, not a fall), "just dropped October
deals" (retail promotions released), "dropping a huge deal event" (a sale event).

## Tie rule

If a headline contains BOTH a realized stock move and a fundamental result,
classify **P**: the defining feature of an echo headline is that the realized
move is reported.

## Original rulebook text (verbatim, from priced_classification.json)

- Step 1 (P): Does the headline state or clearly imply that the company's stock price has ALREADY moved (past/present-perfect tense, e.g. 'dropped 5% after earnings', 'soars after results', 'has gained 5% so far', 'second-best day ever', 'falls below 200-day SMA')? Includes realized moves stated together with a fundamental cause. -> P (realized price move)
- Step 2 (E): Else: is the matched keyword part of a FUNDAMENTAL result or event magnitude (e.g. 'revenue rises 12%', 'sales jump', 'FQ1 gains' expected from earnings) or an analyst catalyst action, with NO realized stock-price move? -> E (fundamental magnitude/event)
- Step 3 (D): Else: is the keyword a FORECAST or expectation of future stock direction ('could sink', 'may drop to $300', 'can it bounce back')? -> D (directional expectation only)
- Step 4 (N): Else: the keyword is incidental with no stock-price meaning ('execution short fall' = shortfall; 'dropped October deals' = retail promotions released). -> N (regex false positive)
- Tie rule: When a headline contains both a realized stock move and a fundamental result (e.g. 'shares jump on blowout results'), classify P: the defining feature of an echo headline is that the realized move is reported.
