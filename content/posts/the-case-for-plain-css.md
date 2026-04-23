---
title: The Case for Plain CSS
date: 2026-01-14
tags: css, web, design
draft: false
---

Every few years the web development community rediscovers that CSS is actually fine. Then it forgets again and builds another abstraction on top of it. We're in a golden age of CSS — container queries, cascade layers, the `:has()` selector — and a lot of developers are still writing utility class soup that obscures what's happening.

## What Plain CSS Gets You

Clarity. When you read `.btn { border: 1px solid currentColor; }` you know what it does. When you read `class="border border-current px-4 py-2 text-sm font-mono"` you have to run a mental compiler to know what it does. That mental compilation is work. Over a codebase, it adds up.

Portability. A CSS file is a CSS file. No build step, no preprocessor, no package to keep current. The styles I wrote five years ago still work.

Longevity. The browser doesn't care that Tailwind is popular. It cares about CSS. CSS has been stable for decades and will be stable for decades more.

## When to Use a Framework

Tailwind is useful on large teams where inconsistency is the main enemy. If you have ten developers and no design system, Tailwind's constraints help. On a personal project or a small team with a style guide, it's overhead.

Component libraries are useful when you need something to look reasonable fast and don't care about differentiation. They're a bad choice when you have a specific aesthetic in mind, because you spend more time fighting the library than writing your own styles.

## The Threshold

Write plain CSS until the maintenance cost of duplication exceeds the maintenance cost of abstraction. For most sites I've built, that threshold is never reached.
