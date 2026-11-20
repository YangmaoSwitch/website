---
title: Where the catalog data comes from
date: 2026-11-20
summary: How each provider's model list is collected, how free models, free quotas and paid models are told apart, how popularity is ranked, and what is still inaccurate.
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

## Popularity

The model list is sorted by popularity by default. The score has three parts: the daily usage OpenRouter publishes on its rankings page, the number of providers that serve the model for free, and a bonus for models released in the last 30 days. OpenRouter only publishes the top 20, so models further down are ranked mostly by provider count.

## What is still inaccurate

- SiliconFlow, Alibaba Cloud Model Studio and some others only show their model lists after sign-in. We use the copies in models.dev, which can lag the console by a few days.
- Tencent Hunyuan has no usable model list source yet.
- "Free quota" follows each provider's general rules. Some promotions cover only certain models; the provider's console is the final word.
- Matching by name occasionally merges two different models or splits one model into two entries.

If you spot a mistake, [submit a correction](../submit.html) and we will verify and update it.
