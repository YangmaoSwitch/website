---
title: Where the catalog data comes from
date: 2026-11-20
summary: How each provider's model list is collected, how free models, free quotas and paid models are told apart, how the lists are ranked, and what is still inaccurate.
draft: true
---

The YangmaoSwitch catalog has two layers: provider entries and model lists. People maintain the provider entries; a script rebuilds the model lists every 6 hours. The website and the desktop app read the same files, published on the `dist` branch of the [catalog repository](https://github.com/YangmaoSwitch/catalog).

## Provider entries

Each provider is one YAML file. It records the unit, period and reset time of every free quota, what sign-up requires, and whether usage stops or switches to paid when the quota runs out. Every quota links to an official source: the provider's docs, pricing page or terms. The entry also records when it was last verified.

This part is not scraped. Quota rules are spread across docs, promotion pages and consoles, each written differently, so we enter them by hand against the original text.

## Model lists

Model lists are merged from four sources:

| Source | What it provides |
|---|---|
| OpenRouter's public API | Every model with prices; a price of 0 counts as a free model |
| [models.dev](https://models.dev) | An open-source model database with each provider's models, prices and capabilities |
| Providers' public model endpoints | ModelScope and NVIDIA for now; no key needed |
| Manual entries | The `free_models` and `models` fields in each entry |

Each model gets one of three labels on each provider:

- **Free model**: the provider lists it as free, or its price is 0. Calls don't use up a quota, but are usually rate-limited.
- **Free quota**: calls draw on credits or vouchers the provider gives away, such as a sign-up token bundle.
- **Paid**: everything else.

The same model has different IDs on different providers, for example `deepseek-ai/DeepSeek-V4.1-Flash` and `deepseek/deepseek-v4.1-flash`. The script strips organization prefixes, date suffixes and case before matching names, which is what lets one page list every provider for a model.

## Ranking

The model list is sorted by "Recommended" by default. The score is the model's own score multiplied by how freely it can be used.

The model score combines several sources so no single site decides: downloads of open-weight models on ModelScope, the number of providers serving the model, daily usage from OpenRouter's rankings page (it only publishes the top 20, so it carries less weight), and the release date. Models released in the last 30 days get a bonus; models older than six months and one year are discounted step by step. Embedding, rerank and speech models are discounted too, since the list is mainly for chat models.

Free access counts the best offer: a free model is 1, a free quota that renews daily or monthly is 0.5, a one-time gift is 0.2, and paid-only offers barely count. Each further provider offering it without charge adds a little, up to 50% more.

Providers are ranked with the same weights: the scores of the models each one serves without charge, multiplied by how freely, added together. Verified providers come before unverified ones.

## What is still inaccurate

- SiliconFlow, Alibaba Cloud Model Studio and some others only show their model lists after sign-in. We use the copies in models.dev, which can lag the console by a few days.
- Tencent Hunyuan has no usable model list source yet.
- "Free quota" follows each provider's general rules. Some promotions cover only certain models; the provider's console is the final word.
- Matching by name occasionally merges two different models or splits one model into two entries.

If you spot a mistake, [submit a correction](../submit.html) and we will verify and update it.
