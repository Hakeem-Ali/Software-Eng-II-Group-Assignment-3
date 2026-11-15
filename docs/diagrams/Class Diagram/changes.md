# Class diagram changes — stakeholder interview

Scope: `docs/diagrams/` only. Files updated in place:

| File | Role |
| --- | --- |
| `class-diagram.puml` | PlantUML source (structural source of truth) |
| `class-diagram.py` | Existing Windows GDI+ renderer (no extra packages) |
| `class-diagram.png` | Rendered image, regenerated with `python docs/diagrams/class-diagram.py` |

The interview transcript has no printed question numbers. Below, **Q1–Q22**
are numbered in document order; quotes are kept short so each point can be
checked against the PDF. `ASSIGNMENT.md`, `docs/ACCEPTANCE.md` and
`app/services/lifecycle.py` are unchanged.

## Changes and the transcript point behind each

| # | Change in the diagram | Transcript point | Detail |
| --- | --- | --- | --- |
| 1 | Reopen target changed from **Submitted** to **Reviewed** | Q5 "would likely go back to the Reviewed status" | `RejectedState.handle()` now returns `ReviewedState`; both transition notes updated. |
| 2 | Reopen is an **administrator-only staff correction** | Q5 "reach out to the admin to correct it"; Q8 "an admin might accidentally reject" | New `ReopenPolicy.can_reopen(actor)` service and `LifecycleService.reopen(...)`. The diagram shows `authorize reopen` on a separate dependency from the employer check, and states that AC 12 covers *advancing*, not reopening. |
| 3 | Only Rejected may be reopened; Hired stays terminal | Q5 (only the mistaken-rejection case is discussed) | Note: submitted/reviewed/shortlisted have no reopen; hires are not reversible. |
| 4 | Only the **listing employer advances** the lifecycle | Q1 "only focus on their own listings and applicants"; AC 12 | `ListingOwnerPolicy.can_advance(actor, listing)`; the employer still cannot reverse a rejection (Q5 contradiction resolved as agreed). |
| 5 | Listing ownership is checked for **reading and listing applicants**, not just transitions | Q1 "own listings and applicants" | `ListingOwnerPolicy.can_read(...)` / `can_list(...)`; `ApplicationService.read_application(...)` / `list_applicants(...)`; `ownership check` dependency drawn from `ApplicationService`. |
| 6 | "Reviewed" requires an explicit employer action | Q15 "clicking a button to mark it as reviewed" | Already covered by `mark_reviewed` / `SubmittedState`; kept unchanged. |
| 7 | Audit row keeps who/when/previous status | Q6 "record who changed ... when ... previous status" | Already covered by `ApplicationHistory`; kept unchanged. |
| 8 | Notification has a **channel**, built from the new status | Q7 "email should be the primary method"; Q12 "status should be consistent across the dashboard" | New `NotificationChannel` enumeration (`EMAIL` primary, `ON_PLATFORM` optional); `Notification.status`, `Notification.channel`, `Notification.text()`; `NotificationService.compose_text(status)`. The same status string feeds email, dashboard and API, so no retry/logging was added (none required for applicant notifications). |
| 9 | Applicant's **active applications vs history** is separable | Q18 "remains in the system for record-keeping ... still view their overall application history" | Minimal `is_active` flag: `Application.is_active`, `ApplicationState.is_active()`, state values (`false` for Rejected/Hired), and `ApplicationService.my_active(...)` / `my_history(...)`. |
| 10 | Admin reopen has its own route | Q5 / Q8 correction path | `BoardRouter` also exposes `POST /applications/{id}/reopen` (admin only). |
| 11 | No withdraw action exists | Q22 "can't withdraw it through the platform" | Kept as-is: there is deliberately no withdraw transition. |
| 12 | No cap on shortlisting | Q16 "shortlist as many as they feel are suitable" | Kept as-is: no limit modelled. |
| 13 | Status set unchanged | Q3 "statuses we already have: Submitted, Reviewed, Shortlisted..." | Kept as-is. |
| 14 | Ordering unchanged (no jumps) | Q2 "Submitted to Reviewed before they can be Shortlisted" | Kept as-is; reopen is the only backward edge. |

## Explicitly not modelled

| Item | Transcript point | Why |
| --- | --- | --- |
| Review substatuses (opened / notes added / discussed) | Q15 "substatuses could be helpful" | Not approved for modelling. AC 11 wants one current status; recorded here as a possible future extension only. |
| Rejection reason shown to applicants | Q18 "providing a reason could be helpful" | Undecided, so no attribute or class was added. |

## Covered elsewhere in the app / out of scope

- **R11 — listing deadline or unpublish:** Q14 says submitted applications survive and applicants still see status. Lifecycle states are unaffected; listing visibility belongs to the listing feature, so no class was added.
- **R15 — one application per listing, no edits after submit:** Q17. `ApplicationService.apply(...)` already owns creation; the duplicate/edit rule belongs to the apply flow, not the state model.
- **R16 — feedback after applying:** Q21. Addressed by the existing notification + audit history; no new lifecycle class.
- **Q4** — applicant-package export and export logging.
- **Q9 / Q10** — subscriber notifications on publish, external-link exclusion, retry/log of failed sends.
- **Q11** — encryption, access controls, security audits.
- **Q13** — resume upload vs manual entry; employer-specified required documents.
- **Q19 / Q20** — subscription eligibility (DCIT), unsubscribing, removing access when ineligible.
- **Q14** — auto-hiding listings from students at deadline/unpublish.

## Consistency fixes (no transcript point)

- The `.puml` and PNG were originally drawn with a composition marker (`*-->`, filled diamond) for `Application` → `ApplicationState`. **This is superseded by Revision 2, fix 5**, which replaces it with a plain association.
- The inherited tracker's `apply_action()` dependency was re-routed outside the "Before" boxes, and three connector routes that previously crossed boxes were re-routed; no content changed.

## Notes on the revision

- Filenames, the `Class Diagram` title, the black-and-white style (`monochrome`, no shadowing) and the before/after comparison with `lifecycle.py` are unchanged.
- Only two new elements were introduced, both directly supported by the transcript: `ReopenPolicy` (admin reopen, change 2) and `NotificationChannel` (change 8).
- `class-diagram.png` was regenerated with the repository's existing GDI+ renderer. PlantUML is not installed on this machine, so the `.puml` was updated but not rendered by PlantUML; the PNG is produced from `class-diagram.py`.
- Nothing outside `docs/diagrams/` was modified.

## Revision 2 — correctness and readability fixes

Only `class-diagram.puml`, `class-diagram.py` and `class-diagram.png` changed in this
revision; no requirement was added or removed. The before/after panels, the
`Class Diagram` title and the black-and-white style are unchanged.

| # | Error fixed | What the diagram now shows |
| --- | --- | --- |
| 1 | **Inheritance** | `abstract class ApplicationState` (was `«interface»`). The five concrete states use a solid generalization line ending in a hollow triangle at the parent, so no `«state»` stereotype is needed. State boxes show methods only; inherited attributes are not repeated. |
| 2 | **Signatures** | One signature everywhere: `handle(action) : ApplicationState`. `Application.apply(action) : str` is a thin adapter that stores the state name returned by `handle(action)`. Legend note and both transition notes updated. |
| 3 | **Exception name** | `IllegalTransitionError` is used consistently in the state note, the exception class and all `throws` dependencies (the truncated `IllegalTransition` is gone). |
| 4 | **Strict chain** | `ReviewedState.allowed_actions() = {shortlist}` — `reject` removed. The legal-transitions note no longer lists `reviewed --reject--> rejected`; rejection is reachable only from Shortlisted. |
| 5 | **Composition** | The filled diamond is replaced by a plain association `Application "1" -- "1" ApplicationState : current state`. States are stateless and factory-created, so `Application` does not own them. Legend row replaced. |
| 6 | **Single source of truth for `is_active`** | `is_active` is no longer a stored flag on `Application`; it appears only as a derived method `is_active() : bool` that delegates to the current state (`false` for Rejected/Hired). |
| 7 | **Layering** | The `Application` ↔ `ApplicationRepository` association is gone. Only `LifecycleService` depends on the repository (dashed dependency, `save`). |
| 8 | **Transition ownership** | `LifecycleService.apply_transition(...)` / `reopen(...)` own every transition, plus `persist_status()`, `record_history()` and `notify_applicant()`. `ApplicationService.transition_application(...)` and `BoardRouter` only delegate; `Application.apply()` is reduced to storing the returned state name. |
| 9 | **Factory** | `StateFactory` is a `«factory»` (replacing the non-standard `«service helper»`) with `from_status(status) : ApplicationState`. It has `«create»` arrows to all five concrete states and `Application.current_state()` depends on it. |
| 10 | **Readability** | Connector labels sit beside their own line with a white background and no longer touch box text (`authorize advance`, `employer_id`/role names, `handle(action)`, `throws`, `history`, `notify`, `«create»`). Long connectors were rerouted so none crosses a class box or spans the full diagram width. Associations carry role names plus multiplicities (`1`, `0..*`, `1..*`). Both panels were re-laid out to remove the bottom empty space (64–78 px margin), body text is 11 pt, titles 13 pt and notes 11 pt, and a 40 px gap separates the before and after panels. |

### Verification of Revision 2

- 25 class and note boxes; **0 overlapping boxes**, **0 connectors passing through a class box**, **0 labels overlapping box text, notes or other labels**.
- All boxes and notes lie inside their panel; content ends 78 px (before) and 64 px (after) above the panel bottom, so the bottom whitespace is gone.
- `.puml` and PNG agree: the same 22 after-panel classes, the same five transitions plus admin reopen, `IllegalTransitionError` present, no `reviewed --reject`, no composition marker, no `«state»`, `abstract class ApplicationState` present, `«factory»` present, 7 `«create»` arrows.
- PlantUML is still not installed, so `class-diagram.puml` remains the structural source and `class-diagram.png` is rendered by `class-diagram.py`; nothing was installed.
- Nothing outside `docs/diagrams/` was modified.

## Revision 3 — small layout and single-source fixes

No design decision changed: `ApplicationState` is still an `«abstract»` class with a
solid generalization and a hollow triangle, the strict chain, the admin-only reopen
(`Rejected → Reviewed`), the terminal `Hired`, the derived `is_active()` and the
absence of an `Application → ApplicationRepository` link are untouched. Only
`class-diagram.puml`, `class-diagram.py`, `class-diagram.png` and this file changed in
this revision.

| # | Fix | What changed |
| --- | --- | --- |
| 1 | **`current state` association** | It is a plain horizontal association from the right edge of `Application` to the left edge of `ApplicationState`, with the label above the line and `1`/`1` at the two ends. It no longer ends on the generalization stem or the hollow triangle, so it cannot be read as inheritance. The `Application`–`ApplicationState` gap was widened to 100 px (`ApplicationState` moved 20 px right) so the label and the two multiplicities sit clear of both boxes. |
| 2 | **Group label** | The five-state group box is now labelled `Concrete states` (top-left, inside the border). The `«create»` label sits above the group and the `throws` label sits 20 px below the group, so neither lies on the group border. |
| 3 | **`«create» history` route** | Re-routed fully outside the crowded area: down the `Application`/`ApplicationState` channel, right along the narrow band above the state group, down the right corridor and back along the band between the bottom row and the notes, then up into the bottom edge of `ApplicationHistory`. It crosses **none** of the `history`, `listing` or `graduate` associations. |
| 4 | **20 px panel margin** | Every box, note, label and connector is now at least 20 px inside its panel (that 20 px is the diagram's own left gutter). The right-hand note was narrowed (right edge 2940, panel edge 2980) and the long right-side connector moved to x = 2950, so nothing touches the border any more. |
| 5 | **Before panel** | `persist flags` now points **from** `applications.transition_application()` **to** `Application` (arrowhead on `Application`'s bottom edge), and the `apply_action()` label sits next to its own elbow, not on the shared vertical. |
| 6 | **Notification** | The stored `status` attribute is gone. `Notification` now shows `+ status() : str  {from Application}` (derived, not persisted) plus `+ text() : str`, so `Application.status` stays the single source of truth. The `.puml` and the consistency note say the same. |
| 7 | **Consistency** | `.puml`, `.py` and the regenerated PNG were updated together and the overlap checks re-run. |

### Verification of Revision 3

- 25 class boxes, 5 notes, 38 labels and 99 connector segments: **0 overlapping boxes**, **0 connectors passing through a box**, **0 labels overlapping box text, notes or other labels**.
- **0 margin problems**: the smallest panel margin is 20 px (the standard left gutter); the right-hand note keeps 40 px and the outermost connector 30 px from the panel edge.
- The `«create» history` line has **0 crossings** with the `history`, `listing` and `graduate` associations. Its only crossings are four perpendicular ones with unrelated connectors (`current state` association, `current_state()`, and the two `«create»` arrows).
- Content still ends 78 px (before) and 64 px (after) above the panel bottom; the panel sizes, title and black-and-white style are unchanged.
- `class-diagram.puml` gained `TransitionApplication ..> InheritedApplication : persist flags`, a comment recording the PNG-only `Concrete states` grouping, and the derived `Notification.status()`; the PNG was re-rendered by `class-diagram.py` (PlantUML is still not installed, nothing was installed).
- Nothing outside `docs/diagrams/` was modified.

## Revision 4 — spacing, routing and label placement

No design decision changed: `ApplicationState` is still an `«abstract»` class with a solid
generalization and a hollow triangle, the strict chain, the admin-only reopen
(`Rejected → Reviewed`), the terminal `Hired`, the derived `is_active()` and the absence of
an `Application → ApplicationRepository` link are untouched. Only `class-diagram.puml`,
`class-diagram.py`, `class-diagram.png` and this file changed in this revision.

| # | Fix | What changed |
| --- | --- | --- |
| 1 | **`StateFactory` / `UnauthorizedTransitionError` gap** | `StateFactory` was narrowed from 360 px to 340 px (x = 2220…2560), leaving exactly a **20 px** gap to `UnauthorizedTransitionError` (x = 2580). Nothing else moved, so the `«create»` arrow under the factory and the `current_state()` arrow into its top edge are unchanged. |
| 2 | **`«create» history` route** | The connector no longer wraps around the state group. It leaves `LifecycleService`'s bottom edge at x = 1305, drops 33 px to the free band under the service row (y = 492), runs left through that band to the new left corridor and drops straight into the top edge of `ApplicationHistory` at x = 840. Path length is 1036 px against 4704 px in Revision 3 (**78 % shorter**). To open that corridor, `Application` was narrowed from 440 px to 400 px and moved 40 px right (x = 860…1260), which keeps its right edge aligned with `LifecycleService`'s left edge and the `current state` association. The `delegates` and `updates status` labels were nudged (`1228,467` and `1084,507`) so the band the new line crosses carries no text. |
| 3 | **Label placement** | `current_state()` now sits at the start of its own line (`1289,744`, 16 px above the y = 760 run) and is **213 px** away from the generalization stem at x = 1570. The `NotificationService → Notification «create»` label moved from just under `IllegalTransitionError` to `2504,1151`, on the long horizontal run of its own arrow, **38 px** below that box and clear of it. |
| 4 | **`Notification` attributes** | The `channel : NotificationChannel` attribute is gone from the class box and from `class-diagram.puml`; the association to `NotificationChannel` (`0..*` / `1`, role `channel`) is kept, so the enumeration is still reachable from `Notification`. The box therefore shrank from 180 px to 161 px and the association's `0..*`, `1` and `channel` labels moved up with its bottom edge. Revision 1's row 8 above still records why the enumeration exists; only the duplicated attribute is removed. |
| 5 | **Consistency** | `.puml`, `.py` and the regenerated PNG were updated together and all overlap checks were re-run. |

### Verification of Revision 4

- 25 class boxes, 5 notes, 38 labels and 97 connector segments: **0 overlapping boxes**, **0 connectors passing through a box**, **0 labels overlapping box text, notes or other labels**.
- **0 margin problems**: the smallest panel margin is still 20 px; the new left corridor puts its line 40 px inside the panel edge (x = 840) and 20 px left of `Application`.
- The `«create» history` line has **0 crossings** — none with the `current state` association, with `current_state()`, with the `history` / `listing` / `graduate` associations, and none with the generalization stem or the state-group rectangle. Total diagram crossings fell from 14 to 10; the remaining 10 are the untouched router-band, `save`/`throws` and `listing`/`graduate` ones.
- `StateFactory` and `UnauthorizedTransitionError` are exactly 20 px apart; the `Notification` box is 161 px tall and its bottom edge is 69 px above `NotificationChannel`.
- Content still ends 78 px (before) and 64 px (after) above the panel bottom; the panel sizes, title and black-and-white style are unchanged.
- Nothing outside `docs/diagrams/` was modified.
