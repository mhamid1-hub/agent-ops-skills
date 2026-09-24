#!/usr/bin/env python3
"""Turn token counts from a tiered plan+execute job into an actual dollar
comparison, so 'this saves money' is a number, not a vibe.

Prices are USD per 1M tokens (input+output blended, editable below — these
drift, treat them as a starting point and override with --prices-file).

Usage:
    python3 cost_estimator.py \
        --planner-model claude-opus-4 --planner-tokens 8000 \
        --executor-model claude-haiku-4 --executor-tokens 40000 \
        --single-tier-model claude-opus-4 \
        --review-fix-tokens 2000
"""
import argparse
import json
import sys

# Blended $/1M tokens, rough public list prices as of authoring — override
# with --prices-file for accuracy against current pricing.
DEFAULT_PRICES = {
    "claude-opus-4": 30.0,
    "claude-sonnet-4-5": 6.0,
    "claude-haiku-4": 1.0,
    "gpt-4o": 5.0,
    "gpt-4o-mini": 0.30,
    "gpt-5": 8.0,
    "deepseek-v3": 0.28,
    "llama-3.1-70b": 0.40,
}


def load_prices(path):
    prices = dict(DEFAULT_PRICES)
    if path:
        with open(path) as f:
            prices.update(json.load(f))
    return prices


def price_for(model, prices):
    if model in prices:
        return prices[model]
    print(f"WARN: no price for '{model}', pass --prices-file with a JSON "
          f"{{\"{model}\": <usd_per_1M_tokens>}} entry. Treating as $0.",
          file=sys.stderr)
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planner-model", required=True)
    ap.add_argument("--planner-tokens", type=int, required=True)
    ap.add_argument("--executor-model", required=True)
    ap.add_argument("--executor-tokens", type=int, required=True)
    ap.add_argument("--review-fix-tokens", type=int, default=0,
                     help="Tokens spent by the strong model fixing defects the review gate caught")
    ap.add_argument("--single-tier-model", required=True,
                     help="Model that would have run the WHOLE job (for comparison)")
    ap.add_argument("--prices-file", help="JSON file overriding/extending DEFAULT_PRICES")
    args = ap.parse_args()

    prices = load_prices(args.prices_file)

    planner_cost = args.planner_tokens / 1_000_000 * price_for(args.planner_model, prices)
    executor_cost = args.executor_tokens / 1_000_000 * price_for(args.executor_model, prices)
    review_fix_cost = args.review_fix_tokens / 1_000_000 * price_for(args.planner_model, prices)
    tiered_total = planner_cost + executor_cost + review_fix_cost

    total_tokens = args.planner_tokens + args.executor_tokens + args.review_fix_tokens
    single_tier_cost = total_tokens / 1_000_000 * price_for(args.single_tier_model, prices)

    print(f"Planner  ({args.planner_model}): {args.planner_tokens:>8,} tok -> ${planner_cost:,.4f}")
    print(f"Executor ({args.executor_model}): {args.executor_tokens:>8,} tok -> ${executor_cost:,.4f}")
    if args.review_fix_tokens:
        print(f"Review/fix ({args.planner_model}): {args.review_fix_tokens:>8,} tok -> ${review_fix_cost:,.4f}")
    print(f"{'—'*50}")
    print(f"Tiered total:                          ${tiered_total:,.4f}")
    print(f"Single-tier equivalent ({args.single_tier_model}, {total_tokens:,} tok): ${single_tier_cost:,.4f}")

    if single_tier_cost <= 0:
        print("\nNo comparison possible (single-tier cost is 0 — check pricing).")
        return

    savings = single_tier_cost - tiered_total
    pct = (savings / single_tier_cost * 100) if single_tier_cost else 0
    if savings > 0:
        print(f"\nSavings: ${savings:,.4f} ({pct:.1f}% cheaper than running it all on {args.single_tier_model})")
    else:
        print(f"\nNO SAVINGS: tiering cost ${-savings:,.4f} MORE than single-tier would have. "
              f"This job was too small / the planner brief overhead ate the savings — "
              f"don't tier by reflex.")


if __name__ == "__main__":
    main()
