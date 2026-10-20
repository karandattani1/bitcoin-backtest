# Dalal Streak

A Duolingo-style learning app for Indian personal finance, capital markets, trading and investing.

Open `index.html` in any browser. It is a single file with no build step, and progress is saved in the browser's local storage.

## What the prototype does

- **Lesson path**: 7 units and 21 bite-sized lessons on a winding path. Each lesson unlocks the next.
- **Seven exercise types**: concept cards, multiple choice, true/false, fill-in-the-blank, type-the-number (₹ calculations with Indian digit grouping such as 1,50,000), match the pairs, and put the steps in order.
- **Game loop**: XP, daily goal (10/20/30/50 XP), day streak, 5 hearts that refill one every 30 minutes, combo counter, badges, confetti and sound effects.
- **Learning from mistakes**: a wrong answer is asked again at the end of the lesson and saved to Practice. "Fix your mistakes" and "Mixed review" never cost hearts and earn one back.
- **Unit guides**: a cheat sheet of every concept card in a unit.
- Keyboard shortcuts (1–4 to pick, Enter to check), light and dark themes, works at phone width.

## Curriculum (India-first)

| Unit | Lessons |
| --- | --- |
| 1. Money Foundations | 50/30/20 budgeting · inflation and the RBI's 4% target, emergency fund · UPI safety, 1930 helpline |
| 2. Safe Savings | FDs, RDs, DICGC ₹5 lakh cover · PPF, EPF, Sukanya Samriddhi, NPS · Rule of 72 |
| 3. Stock Market Basics | NSE, BSE, Sensex, Nifty 50, SEBI · PAN, KYC, Demat (NSDL/CDSL), T+1 · order types, SEBI market-cap buckets |
| 4. Mutual Funds and SIPs | NAV, expense ratio, direct vs regular · SIPs, rupee cost averaging, compounding · index, flexi cap, ELSS, liquid funds, Riskometer |
| 5. Tax Smart (FY 2025-26) | STCG 20%, LTCG 12.5% above ₹1.25 lakh · old vs new regime, 80C, ₹12.75 lakh zero-tax salary · STT, GST, stamp duty, intraday and F&O as business income |
| 6. Trading and Risk | 1% rule, stop-loss, position sizing · futures, options, lots, SEBI's 93% F&O loss study · pre-open, circuits, market-wide breakers |
| 7. Scam Shield | SEBI RIA/RA checks, guaranteed-return red flags, pump-and-dump, SCORES |

All content lives in the `UNITS` array at the top of the script, so adding a lesson is just adding data.

## Roadmap to a real product

1. **Mobile app**: rebuild in React Native (Expo) so it ships on Android first, where most Indian users are. Keep the course as JSON served from a CMS so lessons update without an app release.
2. **Accounts and sync**: Supabase or Firebase for auth (phone OTP), progress, streaks and push reminders ("Your streak ends at midnight").
3. **Languages**: Hindi first, then Tamil, Telugu, Marathi, Bengali and Gujarati. Hinglish copy for the default English track.
4. **Leagues and social**: weekly XP leagues, friend streaks and shareable badges.
5. **Paper trading**: a virtual ₹1,00,000 portfolio on delayed NSE prices, unlocked after Unit 3, with lessons that react to the user's own trades.
6. **Personalised paths**: a short placement quiz (student, first job, trader, parent) that picks the starting unit.
7. **Content upkeep**: a yearly review after each Union Budget and a quarterly check of small-savings rates. Have a SEBI-registered professional review tax and market content.
8. **Compliance**: stay educational. No stock tips, no recommendations, and no broker referral links without the right SEBI registration. Show a clear "not investment advice" note.
9. **Business model**: free core course; a paid tier for unlimited hearts, offline lessons and advanced tracks (options strategies, financial statements, ITR filing). B2B licences for colleges, banks and brokers' investor-education programmes.

*For learning only, not investment advice. Rates and tax rules change, so verify current figures.*
