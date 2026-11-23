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

## Revision 5 — alignment with the implemented State pattern

This revision corrects the diagram to the code that is actually on `main`; it
does not change any application source, test, configuration or requirement.
Only `class-diagram.puml`, `class-diagram.py`, `class-diagram.png` and this
file changed. The `Class Diagram` title, black-and-white style and
Before/After panels are unchanged.

| # | Change in the diagram | Code evidence |
| --- | --- | --- |
| 1 | Removed the invented `ApplicationRepository`, `LifecycleService`, `ApplicationService` and `NotificationService` classes and their dependencies. The After panel now shows the real modules `app.services.applications` and `app.services.lifecycle`, direct `Session(engine)` use, and inline creation of history and notification rows. | `app/services/applications.py:7-24` imports `Session`, `engine` and the real policies; `:49-196` opens sessions directly and has no repository/service classes. `app/database.py:25-32` defines `engine`. |
| 2 | Restored `ReviewedState.allowed_actions() = {shortlist, reject}`. Both `reviewed --reject--> rejected` and `shortlisted --reject--> rejected` are now in the legal-transition note in `.puml`, `.py` and the PNG. | `app/models/application.py:65-77` returns both `SHORTLIST` and `REJECT`; `:80-92` allows `HIRE` and `REJECT`. `tests/test_unit.py:84-96` and `:118-130` exercise these paths. |
| 3 | Corrected the exception story: concrete `handle()` methods, `StateFactory.from_status()` and `Application.apply()` raise `IllegalTransitionError`; the two false `throws` arrows to `UnauthorizedTransitionError` were removed and the exception box now states that it is defined but never raised. | `app/models/application.py:27-32` defines both exceptions; `:52-138` raises `IllegalTransitionError` in state handlers and the factory; `:157-164` raises it for an unknown action. `UnauthorizedTransitionError` has no `raise` site in the repository. |
| 4 | Replaced the invented `Notification.status()` / `text()` design with the stored fields `id`, `user_id`, `application_id`, `listing_id`, `message`, `channel` and `created_at`. The note now says the message is built from the new status, `EMAIL` is the default and `ON_PLATFORM` is defined but unused. | `app/models/notification.py:8-24` defines the enum and all seven fields. `app/services/applications.py:41-46` builds `message` from `application.status` and always passes `NotificationChannel.EMAIL`. |
| 5 | Layering and authorization now match the routes: `BoardRouter` delegates transition/reopen, `applications.py` checks `ListingOwnerPolicy` / `ReopenPolicy`, calls `row.apply(action)` and adds history plus notification; `lifecycle.apply_action()` and `derived_status_from_flags()` are labelled compatibility helpers, not the transition path. | `app/routers/board.py:141-156`; `app/services/applications.py:143-196`; `app/services/lifecycle.py:20-39` and `:42-59`. |
| 6 | Layout fixes without design content: `current_state()` now uses a direct route to `StateFactory`, the `<<create>> notification` dependency starts at `applications.py`, the `throws` arrows start at the concrete-state group and factory, the `Session` / reopen arrow endpoints land on the real box edges, the five state boxes are exactly 20 px apart, and both notes moved up to keep at least 20 px from the panel and neighbouring boxes. | Layout only; no new class or relation beyond the code facts above. |

### Verification of Revision 5

- 26 class boxes, 5 notes, 35 labels and 140 connector segments.
- **0 overlapping boxes**, **0 box gaps below 20 px**, **0 connectors passing through a box**, **0 labels overlapping box text, notes or other labels** and **0 panel-margin problems**.
- `.puml`, `.py` and the regenerated PNG agree on the real modules, the five legal transitions plus admin-only reopen, the actual notification fields, the factory/state exceptions and the absence of the four invented service/repository classes.
- `class-diagram.png` was regenerated with the repository's existing Windows GDI+ renderer; PlantUML is still not installed and nothing was installed.
- Nothing outside `docs/diagrams/` was modified.

## Revision 6 — transition-path-only code alignment

This revision changes only `class-diagram.puml`, `class-diagram.py`,
`class-diagram.png` and this file. The Before panel, the `Class Diagram`
title and the monochrome style are unchanged. The After panel now shows only
participants and calls on the implemented transition and reopen paths.

| # | Change in the diagram | Code evidence |
| --- | --- | --- |
| 1 | Replaced the invented `BoardRouter` participant with the real `app.routers.board` module and drew the exact route paths and signatures `transition(application_id: int, body: TransitionBody) -> dict[str, Any]` and `reopen_application(application_id: int, body: ActorBody) -> dict[str, Any]`. | `app/routers/board.py:10-13` creates `router = APIRouter(...)`; `app/routers/board.py:31-32` and `:42-46` define `ActorBody` and `TransitionBody`; `app/routers/board.py:141-156` define both routes. There is no `BoardRouter` class. |
| 2 | Narrowed the service row to `applications`, `board_auth`, `lifecycle` (`ACTIONS`), `ListingOwnerPolicy`, `ReopenPolicy` and `Session(engine)`, with the real transition/reopen function signatures and `_record_status_change()` signature. | `app/services/applications.py:7-24` imports the real collaborators; `app/services/applications.py:27-46` defines `_record_status_change()`; `app/services/applications.py:143-196` defines `transition_application()` and `reopen_application()`; `app/services/board_auth.py:34-37` defines `get_user()`; `app/services/lifecycle.py:13` defines `ACTIONS`; `app/services/lifecycle.py:42-59` defines the two policies; `app/database.py:25-32` defines `engine`. |
| 3 | Corrected every enum-typed attribute in the After panel and added all five enum boxes with their real members: `ApplicationStatus`, `ApplicationAction`, `ApplyMode`, `ListingStatus` and `NotificationChannel`. | `app/models/application.py:11-24` defines the application enums; `app/models/application.py:141-177` types `Application.status`, `ApplicationHistory.from_status`, `.to_status` and `.action`; `app/models/listing.py:8-16` and `:25-28` type `Listing.apply_mode` and `Listing.status`; `app/models/notification.py:8-10` and `:19` type `Notification.channel`. |
| 4 | Rebuilt the state section around the abstract `ApplicationState` and all five concrete states. The solid generalization edges keep the hollow triangle at the parent. The concrete boxes show `name()`, `allowed_actions()`, `handle()` and `is_active()`; `ReviewedState.allowed_actions()` explicitly contains both `SHORTLIST` and `REJECT`. | `app/models/application.py:35-49` defines the abstract interface; `app/models/application.py:52-62`, `:65-77`, `:80-92`, `:95-108` and `:111-122` define the five concrete states. `app/models/application.py:69-70` returns both `ApplicationAction.SHORTLIST` and `ApplicationAction.REJECT`. |
| 5 | Rewrote the legal-transition note to the implemented edges only: `MARK_REVIEWED`, `SHORTLIST`, `REJECT` from both reviewed and shortlisted, `HIRE`, admin-only `REOPEN` to reviewed, terminal hired, and `IllegalTransitionError` for unknown or illegal inputs. | `app/models/application.py:59-62`, `:72-77`, `:87-92`, `:102-105`, `:118-119`, `:125-138` and `:157-164`. `tests/test_unit.py:93-130` and `:133-151` exercise these state outcomes. |
| 6 | Replaced the old authorization wording with the implemented calls: `board_auth.get_user()`, `lifecycle.ACTIONS`, `ListingOwnerPolicy.can_advance()` requiring the employer role and matching `listing.employer_id`, and `ReopenPolicy.can_reopen()` requiring admin. | `app/services/applications.py:146-157` and `:173-175`; `app/services/board_auth.py:34-37`; `app/services/lifecycle.py:13` and `:42-59`. |
| 7 | Drew audit and notification as rows created through `Session(engine)` by `_record_status_change()`, with `Notification.channel` set to `NotificationChannel.EMAIL`. | `app/services/applications.py:27-46`, `:152-169` and `:177-195`; `app/models/notification.py:8-10` and `:13-24`. |
| 8 | Removed earlier After-panel content that is not on the transition/reopen path, and removed the related note wording, so the diagram no longer labels non-path material as part of the design. | `app/services/applications.py:143-196` calls only `get_user`, `ACTIONS`, the two policies, `Application.apply()`, `Session` and `_record_status_change()` on these paths. |
| 9 | Moved the subtitle, compacted the applications service box, and rerouted the association, create and generalization connectors so all boxes keep at least 20 px separation and no connector crosses a box. | Layout only in `docs/diagrams/Class-Diagram/class-diagram.py:456-472` and `:593-1068`; no application code was changed. |
| 10 | Regenerated the PNG from the updated renderer and rewrote the structural `.puml` After section so the source, renderer and image agree on the same participants, enums, states and transitions. | `docs/diagrams/Class-Diagram/class-diagram.py:593-1068`; `docs/diagrams/Class-Diagram/class-diagram.puml:47-end`. PlantUML is not installed, so the PNG came from the repository GDI+ renderer. |

### Verification of Revision 6

- `python -B` with `PYTHONDONTWRITEBYTECODE=1` parsed the renderer and regenerated
  `class-diagram.png`; no packages were installed and no tests were run.
- A temporary layout checker outside the repository measured 34 rectangles,
  128 line segments and 247 text runs: **minimum box gap 20.0 px**, **0 gaps
  below 20 px**, **0 boxes outside the After panel**, **0 connectors passing
  through a box**, **0 text/text overlaps** and **0 text runs overflowing their
  containing box**.
- `.puml`, `.py` and the PNG agree: five enum boxes, typed enum attributes,
  all five concrete states, both `REJECT` transitions from `ReviewedState`,
  admin-only reopen to `ReviewedState`, and no non-path participants.
- Nothing outside the four class-diagram files was modified.

## Revision 7 — design-level enum and transition update

Base: this revision restarts from the committed **design-level** version of
`class-diagram.puml` and `class-diagram.py`, not the Revision 6 "as implemented"
working-tree files. The base was read from git commit
`244fbe7d9d5e8152527a8e56882808378b1304c9` (the files were last changed in
`bc3eda34728fad7acad5d379063b26879032ff6e`). The Before panel, the abstract
`ApplicationState` with solid generalization lines, the "Concrete states" group,
the admin-only reopen, terminal Hired, both exceptions, the `Class Diagram`
title and the black-and-white style are unchanged.

| # | Change | What the diagram now shows |
| --- | --- | --- |
| 1 | Reviewed -> Rejected allowed | `ReviewedState.allowed_actions() = {shortlist, reject}`; `handle(action)` returns `ShortlistedState \| RejectedState`; the legal-transitions note gains `reviewed --reject--> rejected` and is retitled "Legal transitions, reopen rule and active vs history". |
| 2 | Application status enum | New `<<enumeration>> ApplicationStatus` (`SUBMITTED`, `REVIEWED`, `SHORTLISTED`, `REJECTED`, `HIRED`). `Application.status`, `Application.apply(action)`, `ApplicationHistory.from_status` / `to_status`, `Notification.status()`, `NotificationService.notify_status_change(... status)`, `ApplicationState.name()` and `StateFactory.from_status(status)` use the enum; notes say the status is stored as `ApplicationStatus`. |
| 3 | Listing status enum | New `<<enumeration>> ListingStatus` (`PENDING`, `PUBLISHED`, `UNPUBLISHED`) and `Listing.status : ListingStatus`. |
| 4 | Notification channel enum attribute | `Notification.channel : NotificationChannel` is shown again; `NotificationChannel` keeps `EMAIL {primary}` and `ON_PLATFORM {optional}`. |
| 5 | Enum links | All three enums are linked the same way: a short plain line labelled with the owning attribute (`status`, `status`, `channel`) to an adjacent enumeration box. |
| 6 | Cosmetic apostrophes | Literal apostrophe separators in method and note text were replaced with ` - `; only genuine PlantUML comment lines still start with an apostrophe. |

### Verification of Revision 7

- `python -B` with `PYTHONDONTWRITEBYTECODE=1` regenerated `class-diagram.png`;
  no packages were installed and no tests were run.
- Inline checker over the renderer: **32 boxes**, **110 connector segments** and
  **38 labels**; **minimum box gap 20.0 px**, **0 gaps below 20 px**,
  **minimum panel margin 20.0 px**, **0 margins below 20 px**,
  **0 connectors passing through a box**, **0 label/text overlaps**,
  **0 label/label overlaps**, **0 label/border overlaps**,
  **0 text runs overflowing their containing box**. Canvas is 3000 x 1820 px
  and the minimum font size is 10 pt.
- `.puml`, `.py` and the regenerated PNG agree on the six changes above.
- Nothing outside the four class-diagram files was modified.

## Revision 8 — enum check and Application association spacing

This revision only spreads the three `Application` association lines in the
renderer and moves each label beside its own line end. No class, method,
relationship or enum name was changed. The `.puml` already carries the correct
roles and multiplicities, so it needed no text edit for this layout-only fix;
`class-diagram.py` was edited and `class-diagram.png` was regenerated with the
repository's existing GDI+ renderer.

### Enum name check (no diagram edits)

| Enum | Diagram name and members | Code name and members | Match | Code evidence |
| --- | --- | --- | --- | --- |
| Application status | `ApplicationStatus` — `SUBMITTED`, `REVIEWED`, `SHORTLISTED`, `REJECTED`, `HIRED` (`class-diagram.puml:106-112`) | `ApplicationStatus` — `SUBMITTED="submitted"`, `REVIEWED="reviewed"`, `SHORTLISTED="shortlisted"`, `REJECTED="rejected"`, `HIRED="hired"` | Yes | `app/models/application.py:11-16` |
| Listing status | `ListingStatus` — `PENDING`, `PUBLISHED`, `UNPUBLISHED` (`class-diagram.puml:202-206`) | `ListingStatus` — `PENDING="pending"`, `PUBLISHED="published"`, `UNPUBLISHED="unpublished"` | Yes | `app/models/listing.py:13-16` |
| Notification channel | `NotificationChannel` — `EMAIL {primary}`, `ON_PLATFORM {optional}` (`class-diagram.puml:186-189`) | `NotificationChannel` — `EMAIL="EMAIL"`, `ON_PLATFORM="ON_PLATFORM"` | Yes (the braces are design annotations, not member names) | `app/models/notification.py:8-10` |
| Application action | Not present as an enum box | `ApplicationAction` — `MARK_REVIEWED="mark_reviewed"`, `SHORTLIST="shortlist"`, `REJECT="reject"`, `HIRE="hire"`, `REOPEN="reopen"` | Not compared; left unchanged | `app/models/application.py:19-24` |
| Apply mode | Not present as an enum box | `ApplyMode` — `EXTERNAL_LINK="external-link"`, `ON_PLATFORM_COLLECT="on-platform-collect"` | Not compared; left unchanged | `app/models/listing.py:8-10` |

The typed fields still named by the diagram were checked against:
`Application.status` (`app/models/application.py:147` and `:152`),
`ApplicationHistory.from_status` / `to_status` / `action`
(`app/models/application.py:173-175`), `Listing.apply_mode` and `Listing.status`
(`app/models/listing.py:25` and `:28`), and `Notification.channel`
(`app/models/notification.py:19`). Because the three diagram enum names and
members match the code, no enumeration box and no attribute type was edited.
`ApplicationAction` and `ApplyMode` exist in code but have no diagram enum box;
adding boxes for them would change the design, so they are reported only.

### Cosmetic fix

| # | Change | Result |
| --- | --- | --- |
| 1 | Spread the source verticals | `ApplicationHistory`, `Listing` and `User` now leave `Application` at x = 1125, 1150 and 1175 px: **25 px** between adjacent lines. |
| 2 | Spread the routed horizontals | The `Listing` and `User` lines turn at y = 1025 and 1000 px: **25 px** apart. The three lines have **0** mutual crossings. |
| 3 | Label placement | `1` sits at the `Application` end of `history`; `0..*` and `history` sit at its `ApplicationHistory` end. `0..*` sits at the `Application` end of `listing`; `1` and `listing` sit at its `Listing` end. `0..*` sits at the `Application` end of `graduate`; `1` and `graduate` sit at its `User` end. No label crosses a connector or the `Concrete states` border. |
| 4 | Consistency | The `.puml` semantics are unchanged, the `.py` layout was edited, and the `.png` was regenerated. |

### Verification of Revision 8

- `PYTHONDONTWRITEBYTECODE=1 python -B` regenerated `class-diagram.png` and ran
  the inline layout checker; no packages were installed and no tests were run.
- Canvas **3000 x 1820 px**; **32 boxes**, **110 connector segments** and
  **38 labels**; **minimum box gap 20.0 px**, **0 gaps below 20 px**,
  **minimum panel margin 20.0 px**, **0 margins below 20 px**,
  **0 connectors passing through a box**, **0 label/text overlaps**,
  **0 label/label overlaps**, **0 label/border overlaps**,
  **0 text runs overflowing a box** and **minimum font 10 pt**.
- The three `Application` source verticals are **25 px / 25 px** apart, the two
  routed horizontals are **25 px** apart, and the nine moved labels have
  **0 connector hits** and **0 group-border overlaps**.
- Nothing outside the four class-diagram files was modified.

## Revision 9 — subscription model and notification multiplicities

This revision adds the `Subscription` model and makes the notification
multiplicities visible in the After panel. The Before panel, the state pattern,
the `Class Diagram` title, the monochrome style and all unrelated classes and
notes are unchanged. Only `class-diagram.puml`, `class-diagram.py`,
`class-diagram.png` and this file changed.

| # | Change | Evidence / result |
| --- | --- | --- |
| 1 | New `Subscription <<model>>` with `id : int` and `graduate_id : int` | `app/models/subscription.py:6-8` defines exactly those two fields. |
| 2 | New `Subscription "0..1" --> "1" User : graduate` | `Subscription.graduate_id` is a unique FK (`app/models/subscription.py:8`) and `listings.subscribe()` rejects duplicates (`app/services/listings.py:24-28`), so at most one row exists per graduate. |
| 3 | New `Notification "0..*" --> "1" User : recipient` | `Notification.user_id` is a non-unique FK (`app/models/notification.py:15`); all three creation sites set it (`app/services/applications.py:42`, `app/services/listings.py:107` and `:133`). |
| 4 | `Notification` – `NotificationChannel` now shows its `1` / `1` multiplicities in the PNG | The `.puml` association already carried `1` / `1`; the renderer previously drew only the `channel` role label. |

### Verification of Revision 9

- `PYTHONDONTWRITEBYTECODE=1 python -B` regenerated `class-diagram.png`; no
  packages were installed and no tests were run.
- Inline checker over the renderer: canvas **3000 x 1820 px**, **28 boxes**,
  **5 notes**, **116 connector segments** and **46 labels**; **minimum box gap
  20.0 px**, **minimum panel margin 20.0 px**, **0 connectors passing through a
  box**, **0 label/label overlaps** and **0 label/border overlaps**. The new
  labels introduce **0 new label/text overlaps** and **0 new text overflows**
  compared with the committed baseline.
- `.puml`, `.py` and the regenerated PNG agree on the Subscription class, the
  `0..1`/`1` graduate association, the `0..*`/`1` recipient association and the
  `1`/`1` channel multiplicities.
- Nothing outside the four class-diagram files was modified.
