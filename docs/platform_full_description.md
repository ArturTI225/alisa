# Platform Full Description

## Purpose and Principles
- Social, non-commercial volunteer platform: no prices, fees, or payment flows.
- Core lifecycle: help request -> match -> accept -> complete -> gratitude/review.
- Instant booking is secondary; the primary path is request > match > accept.
- Prioritize safety, auditability, and clarity of status for all parties.

## Roles and Access
- Roles: requester, volunteer, organization, admin.
- User core fields: email, phone (both verifiable), is_active, is_blocked, role, created_at, updated_at.
- Access model: role-based access control plus object-level permissions; audit log for sensitive actions; rate limiting on APIs; soft delete for reversible removals.

## Non-Monetary Constraints
- No payment processing in core; no prices, tariffs, or commissions.
- Do not add payment-related fields (price/amount/currency) to core entities.
- Reviews and reputation exclude money signals (no “price/quality” ratings).

## Domain Entities
- User: identity, contact, role flags, activity state.
- VolunteerProfile: 1:1 with User; skills/categories; availability; verification_status; total_hours_helped; completed_requests; badges earned.
- HelpRequest: created_by (user or organization); title; description; category; location (city/region); urgency (low | medium | high); status (open | in_review | matched | in_progress | done | cancelled); attachments (images/docs).
- VolunteerApplication: help_request; volunteer; message; status (pending | accepted | rejected | withdrawn); timestamps.
- Verification: user; type (email | phone | id_document); status (pending | approved | rejected); evidence or reference data.
- Report: reported_user and/or request; reason; status; admin_notes; timestamps.
- Badge: name; criteria (hours served and/or requests completed); earned_at; awarded_by (admin/system).
- CompletionCertificate: issued for completed help; linked to help_request and volunteer; stored as PDF; includes timestamps and summary.
- AuditLog: actor; action; target object; timestamp; metadata (IP, user agent); stored immutably.

## Core Workflows
- Help request creation: requester/organization submits title, description, category, location, urgency, attachments; status starts as open or in_review (if moderation applies).
- Matching:
  - Standard flow: request stays open, volunteers apply; requesters or admins review applications and accept/reject; accepted application sets HelpRequest status to matched/in_progress.
  - Instant booking: secondary path; requester may select a volunteer directly and move to accepted/in_progress without the application queue.
  - Matching criteria: skills/categories fit, availability, location proximity, urgency, and verification level.
- Application lifecycle: pending -> accepted/rejected/withdrawn. When accepted, the request becomes matched/in_progress; when work starts, status in_progress; on completion, status done; cancellation returns status to cancelled.
- Progress and completion: record timestamps for acceptance, start, and completion; collect confirmation from requester (and optionally volunteer); trigger certificate generation; update volunteer stats (hours, completed_requests) and badge eligibility.
- Cancellations and withdrawals: both requester and volunteer can cancel/withdraw before in_progress; post-start cancellations may require admin review; notify parties and log reasons (no payment side-effects).

## Gratitude and Reputation
- Reviews allowed only after status done; focus on reliability, punctuality, and attitude.
- No monetary aspects in reviews; gratitude messages and thank-you notes are encouraged.
- Stats update on completion: total_hours_helped, completed_requests, monthly activity snapshots.
- Badges auto-awarded by criteria (hours/requests) with audit trail; admins can grant/revoke.
- Completion certificates (PDF) confirm volunteer activity; useful for students and NGOs.

## Trust, Safety, and Compliance
- Identity verification: email, phone, and ID document checks; statuses pending/approved/rejected; re-verification on expiry or risk events.
- Moderation: HelpRequests can enter in_review; admins can pause, edit, or reject; audit all changes.
- Reporting: users can report other users or requests; admins triage and resolve; outcomes recorded in admin_notes.
- Blocks and restrictions: is_blocked flag prevents participation; soft delete preserves history while hiding content.
- Data handling: store audit logs for sensitive actions; apply rate limits to prevent abuse; enforce least-privilege access to files and objects.

## Communications and Notifications
- Channels: email and SMS for verification; in-app and email for status changes (applications, acceptances, cancellations, completions); chat for requester-volunteer coordination when in_progress.
- Delivery: use Celery + Redis for async delivery and retries; template-based messages; localization-aware content.

## Frontend (Next.js)
- Next.js with SSR for public and authenticated pages; i18n with Romanian supported (RO); extendable to additional locales; UI avoids any pricing references.
- Accessibility: keyboard navigation, ARIA labels, readable contrast, focus states.
- UX: clear state for request and application lifecycles; instant booking path distinct from apply/review path; upload support for attachments; responsive layouts.

## Backend (Django / DRF)
- Django 5 + DRF APIs; role-based and object-level permissions on requests, applications, and reports.
- Celery + Redis for background jobs (notifications, certificate/PDF generation, cleanups).
- Storage: S3-compatible object storage for attachments and generated PDFs.
- Security: rate limiting on sensitive endpoints; audit logging; soft delete on user-generated content; request/response validation.

## Data Quality and Reporting
- Metrics: counts of open/in_review/matched/in_progress/done requests; volunteer hours; completion rates; cancellation reasons and rates; admin interventions; verification pass rates.
- Badges: auto-award based on hours served and requests completed; admins can grant or revoke with audit trail.
- Exports: CSV/PDF summaries for admins and organizations; certificates for volunteers on completion.

## Operational Notes
- Keep history: retain state transitions and timestamps on HelpRequest and VolunteerApplication objects.
- Observability: structured logs, error tracking, and basic health metrics for web, worker, and storage.
- Backups: periodic backups of database and object storage metadata; test restore paths.

## Architectural Boundaries (For AI Implementation)
- Core Help Flow: HelpRequest, VolunteerApplication, statuses, completion.
- Trust & Safety: Verification, Report, AuditLog, moderation tooling.
- Recognition: Badges, CompletionCertificate, volunteer stats.
- Admin & Analytics: Moderation tools, exports, dashboards.

## State Machines
- HelpRequest.status: open -> in_review -> matched -> in_progress -> done; open -> cancelled; in_progress -> cancelled (admin review).
- VolunteerApplication.status: pending -> accepted -> in_progress; pending -> rejected; pending -> withdrawn.

## Explicit Prohibitions for AI
- Do not introduce prices, costs, or financial incentives.
- Do not add paid visibility or featured listings.
- Do not correlate reputation with any monetary signals.

## Admin Panel (Required)
- Moderates requests (approve/reject/edit), confirms volunteers, processes reports, and blocks users.
- Views analytics: help volume, activity by region, categories of help, verification throughput.
- Manages badges/certificates issuance and revocation with audit trail.

## Success Criteria and Focus
- Safely connect people needing help with volunteers without any monetary dependency.
- Built-in trust and safety (verification, moderation, audit logs) from the start.
- Scalable architecture for web and workers; observability and backups in place.
- Always interpret features through social impact, trust, and safety—not commerce.
