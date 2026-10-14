# Dark study workspace refresh

The existing application now uses a shared visual layer inspired by iOS Health
and Activity: grouped dark surfaces, rounded controls, a restrained accent color,
consistent navigation icons, and a completion ring based on real course progress.
Cards and menus use eased transitions; system reduced-motion preferences disable
these effects. Existing learning and persistence flows are preserved.

The Electron window uses a draggable title strip matching the app background and
native Windows window controls. The desktop icon now renders with transparency,
and the icon is included in both the window configuration and packaged files.

The C++ section 1.1 quiz failed because quoted textbook sentences were inserted
into strict JSON-schema enum literals. Evidence is now supplied as prompt data,
with the existing local validation still requiring a quotation from the reading.
The corrected quiz was created successfully and is cached. This does not add OCR;
unreadable scanned sections still require OCR before generation.

Validation:

- 64 backend tests passed, including a regression for quoted textbook evidence.
- Frontend lint and production compilation passed.
- Playwright checked library retry, chat failure/draft recovery, local Monaco,
  code execution controls, mobile overflow and reduced-motion styling.
- Actual C++ path and lesson screens were inspected; the saved quiz endpoint
  returned questions successfully without regeneration.
- Desktop smoke checks passed for onboarding, encrypted keys, separate profiles,
  themes, local Monaco, the title strip and native window-control visibility.
- Static review found no important regressions; secret scanning found no keys in
  tracked files or reachable Git history.

README setup is shorter; detailed installer instructions remain in
[desktop.md](desktop.md). The editor remains a large lazy-loaded bundle.
Windows display scaling and the final installed appearance should also be checked
on the user's normal desktop.
