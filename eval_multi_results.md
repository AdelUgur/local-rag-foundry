# Multi-Document Evaluation Results

Corpus: 4 overlapping documents (`laptop-policy.md`, `lab-safety.md`, `printing-guide.md`, `membership-faq.md`).
Gate threshold: **0.4**. Top-K: **5**.

## Summary

| Measure | Result |
|---|---|
| Correct file retrieved (in top-5) | 11/11 |
| Correct file ranked #1 | 11/11 |
| Correct fact in the answer | 11/11 |
| Correct file cited | 11/11 |
| Answers citing a **wrong** file | 2/11 |
| Non-answerable questions handled | 5/5 |

Verdicts: **PARTIAL** 2, **PASS** 14

## Per-question results

| # | Question | Expected file | Score | s | Gated | Retrieved | Top-1 | Content | Cited | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | How long can I borrow a laptop for? | laptop-policy.md | 0.709 | 6.0 | no | yes | yes | yes | yes | **PARTIAL** |
| 2 | How much is the deposit for a laptop? | laptop-policy.md | 0.625 | 5.0 | no | yes | yes | yes | yes | **PASS** |
| 3 | How much is the filament deposit for the 3D printer? | printing-guide.md | 0.708 | 5.3 | no | yes | yes | yes | yes | **PASS** |
| 4 | How far in advance do I have to book the 3D printer? | printing-guide.md | 0.694 | 5.5 | no | yes | yes | yes | yes | **PASS** |
| 5 | How long is a lab induction valid for? | lab-safety.md | 0.755 | 5.7 | no | yes | yes | yes | yes | **PARTIAL** |
| 6 | When are the lab induction sessions held? | lab-safety.md | 0.710 | 6.8 | no | yes | yes | yes | yes | **PASS** |
| 7 | How much does membership cost? | membership-faq.md | 0.633 | 5.1 | no | yes | yes | yes | yes | **PASS** |
| 8 | When does the club meet? | membership-faq.md | 0.593 | 5.1 | no | yes | yes | yes | yes | **PASS** |
| 9 | Which filament types are allowed in the 3D printer? | printing-guide.md | 0.610 | 6.4 | no | yes | yes | yes | yes | **PASS** |
| 10 | I have never been to the workshop. What do I need before I can book... | printing-guide.md | 0.716 | 8.5 | no | yes | yes | yes | yes | **PASS** |
| 11 | Who do I report a workshop injury to, and how quickly? | lab-safety.md | 0.565 | 4.7 | no | yes | yes | yes | yes | **PASS** |
| 12 | Is there a coffee machine in the workshop? | – | 0.433 | 3.9 | no | – | – | yes | – | **PASS** |
| 13 | What is the wifi password? | – | 0.343 | 0.1 | yes | – | – | yes | – | **PASS** |
| 14 | Tell me a joke. | – | 0.301 | 0.1 | yes | – | – | yes | – | **PASS** |
| 15 | Who won the 2022 World Cup? | – | 0.214 | 0.1 | yes | – | – | yes | – | **PASS** |
| 16 | (empty) | – | 0.000 | 0.0 | yes | – | – | yes | – | **PASS** |

## Answers in full

### 1. How long can I borrow a laptop for?

*Fact is stated in two files (14 days / two weeks) - consistency check.*

- Expected source: `laptop-policy.md`
- Retrieved: `laptop-policy.md`, `membership-faq.md`, `laptop-policy.md`, `laptop-policy.md`, `printing-guide.md`
- Cited: `laptop-policy.md`, `membership-faq.md`, `printing-guide.md`
- Top score: 0.709  ·  6.0s  ·  gated: no
- **Cited the wrong file:** printing-guide.md
- Verdict: **PARTIAL**

> According to the context, a member can borrow a laptop for up to two weeks at a time.

### 2. How much is the deposit for a laptop?

*TRAP: printing-guide.md also has a deposit (100 TL).*

- Expected source: `laptop-policy.md`
- Retrieved: `laptop-policy.md`, `laptop-policy.md`, `laptop-policy.md`, `printing-guide.md`, `membership-faq.md`
- Cited: `laptop-policy.md`
- Top score: 0.625  ·  5.0s  ·  gated: no
- Verdict: **PASS**

> The deposit for a laptop is **500 TL**.

### 3. How much is the filament deposit for the 3D printer?

*TRAP: the other half of the deposit pair.*

- Expected source: `printing-guide.md`
- Retrieved: `printing-guide.md`, `printing-guide.md`, `printing-guide.md`, `laptop-policy.md`, `laptop-policy.md`
- Cited: `printing-guide.md`
- Top score: 0.708  ·  5.3s  ·  gated: no
- Verdict: **PASS**

> The filament deposit for the 3D printer is **100 TL**.

### 4. How far in advance do I have to book the 3D printer?

*Single-source fact, should be easy.*

- Expected source: `printing-guide.md`
- Retrieved: `printing-guide.md`, `printing-guide.md`, `membership-faq.md`, `laptop-policy.md`, `printing-guide.md`
- Cited: `printing-guide.md`
- Top score: 0.694  ·  5.5s  ·  gated: no
- Verdict: **PASS**

> You must book the 3D printer **at least 48 hours in advance**.

### 5. How long is a lab induction valid for?

*TRAP: several documents mention durations.*

- Expected source: `lab-safety.md`
- Retrieved: `lab-safety.md`, `printing-guide.md`, `laptop-policy.md`, `membership-faq.md`, `membership-faq.md`
- Cited: `lab-safety.md`, `laptop-policy.md`
- Top score: 0.755  ·  5.7s  ·  gated: no
- **Cited the wrong file:** laptop-policy.md
- Verdict: **PARTIAL**

> A lab induction is valid for 12 months from the date of the session.

### 6. When are the lab induction sessions held?

*TRAP: membership-faq.md also has a recurring weekday (Thursday).*

- Expected source: `lab-safety.md`
- Retrieved: `lab-safety.md`, `printing-guide.md`, `membership-faq.md`, `membership-faq.md`, `membership-faq.md`
- Cited: `lab-safety.md`
- Top score: 0.710  ·  6.8s  ·  gated: no
- Verdict: **PASS**

> from lab-safety.md
> # Lab Safety and Induction
> 
> Induction sessions are held on the **first Monday of each month at 10:00** in the workshop itself.

### 7. How much does membership cost?

*TRAP: two other documents contain money amounts.*

- Expected source: `membership-faq.md`
- Retrieved: `membership-faq.md`, `membership-faq.md`, `laptop-policy.md`, `lab-safety.md`, `membership-faq.md`
- Cited: `membership-faq.md`
- Top score: 0.633  ·  5.1s  ·  gated: no
- Verdict: **PASS**

> According to the membership FAQ, membership costs 150 TL per academic year.

### 8. When does the club meet?

*TRAP: Room B204 appears in two documents.*

- Expected source: `membership-faq.md`
- Retrieved: `membership-faq.md`, `membership-faq.md`, `membership-faq.md`, `lab-safety.md`, `laptop-policy.md`
- Cited: `membership-faq.md`
- Top score: 0.593  ·  5.1s  ·  gated: no
- Verdict: **PASS**

> The club meets every Thursday at 18:00.

### 9. Which filament types are allowed in the 3D printer?

*Needs both items, not just one.*

- Expected source: `printing-guide.md`
- Retrieved: `printing-guide.md`, `printing-guide.md`, `printing-guide.md`, `laptop-policy.md`, `membership-faq.md`
- Cited: `printing-guide.md`
- Top score: 0.610  ·  6.4s  ·  gated: no
- Verdict: **PASS**

> According to the provided context, only PLA and PETG filaments are allowed in the 3D printer. ABS filament is not permitted due to ventilation issues.

### 10. I have never been to the workshop. What do I need before I can book the 3D printer, and when can I get it?

*MULTI-HOP: requirement is in printing-guide.md, the schedule is in lab-safety.md. Needs both files at once.*

- Expected source: `printing-guide.md`
- Retrieved: `printing-guide.md`, `printing-guide.md`, `membership-faq.md`, `lab-safety.md`, `laptop-policy.md`
- Cited: `printing-guide.md`
- Top score: 0.716  ·  8.5s  ·  gated: no
- Verdict: **PASS**

> Before you can book the 3D printer, you need to have a **valid lab induction**. You can attend an induction session, which is held on the **first Monday of each month at 10:00**. After completing the induction, you will be eligible to book the printer.

### 11. Who do I report a workshop injury to, and how quickly?

*TRAP: 'within 24 hours' also appears in printing-guide.md for failed prints.*

- Expected source: `lab-safety.md`
- Retrieved: `lab-safety.md`, `lab-safety.md`, `membership-faq.md`, `printing-guide.md`, `lab-safety.md`
- Cited: `lab-safety.md`
- Top score: 0.565  ·  4.7s  ·  gated: no
- Verdict: **PASS**

> You should report a workshop injury to the lab coordinator within 24 hours.

### 12. Is there a coffee machine in the workshop?

*GATE TEST: sounds exactly like the corpus, but no document answers it.*

- Expected source: `none`
- Retrieved: `laptop-policy.md`, `lab-safety.md`, `lab-safety.md`, `membership-faq.md`, `printing-guide.md`
- Top score: 0.433  ·  3.9s  ·  gated: no
- Verdict: **PASS**

> I don't have that in your notes.

### 13. What is the wifi password?

*GATE TEST: plausible club question, absent from the corpus.*

- Expected source: `none`
- Retrieved: `laptop-policy.md`, `lab-safety.md`, `membership-faq.md`, `laptop-policy.md`, `printing-guide.md`
- Top score: 0.343  ·  0.1s  ·  gated: yes
- Verdict: **PASS**

> I don't have that in your notes.

### 14. Tell me a joke.

*The case that failed on the single-document corpus.*

- Expected source: `none`
- Retrieved: `lab-safety.md`, `membership-faq.md`, `laptop-policy.md`, `membership-faq.md`, `membership-faq.md`
- Top score: 0.301  ·  0.1s  ·  gated: yes
- Verdict: **PASS**

> I don't have that in your notes.

### 15. Who won the 2022 World Cup?

*Baseline: should score far below the gate.*

- Expected source: `none`
- Retrieved: `laptop-policy.md`, `membership-faq.md`, `printing-guide.md`, `membership-faq.md`, `lab-safety.md`
- Top score: 0.214  ·  0.1s  ·  gated: yes
- Verdict: **PASS**

> I don't have that in your notes.

### 16. (empty input)

*Edge case: empty input.*

- Expected source: `none`
- Retrieved: –
- Top score: 0.000  ·  0.0s  ·  gated: yes
- Verdict: **PASS**

> (no input)

---

Verdicts are assigned by keyword matching and are a first pass only. Keyword matching cannot distinguish "PLA is allowed" from "PLA is not allowed", so read the answers above before trusting the table.
