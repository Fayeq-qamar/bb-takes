# Sharing BB Takes and who gets access

There are two separate things to share:

1. **The tool itself**: the zip. Everyone who uses BB Takes needs this. No GitHub account needed.
2. **The GitHub repo**: only for people who maintain it or send fixes. It stays **private**.

## 1. Sharing the zip (everyone)
- The maintainer builds it with `bash scripts/make_release.sh` → `dist/BB_Takes_vX.Y.Z.zip` (≈ 57 MB, includes ffmpeg).
- Share it the way the team already shares files: Slack/WhatsApp, Google Drive, or a `Tools` folder on the
  shoot server. (Claude can't write to the server, so a person with write access copies it there.)
- People unzip it and follow `docs/SETUP.md`. When there's a new version, they replace the folder; their exports
  and previews are kept.

## 2. The private GitHub repo (maintainers)

### Who can see it
A private repo is visible only to its owner and the people invited to it. Nobody else can find, view or clone it.

### Inviting someone
GitHub › the `bb-takes` repo › **Settings › Collaborators** › **Add people** › their GitHub username or email.
They get an email invite and must accept it. Remove them from the same page at any time.

Or from Terminal: `gh api -X PUT repos/<owner>/bb-takes/collaborators/<their-username> -f permission=push`

### What they can do: depends on where the repo lives
**On your personal account (simplest, what we start with):**
- Personal repos have only one level for invitees: **collaborator = read + write** (they can push changes).
- Collaborators can also **fork** it; their fork stays private, and disappears if you remove them.
- Good for a small group of trusted people who'll actually change the code.

**In a GitHub Organization (when you want finer control):**
- Create a free organization (GitHub › your avatar › Your organizations › New organization › Free), e.g. `bb-team`,
  then transfer the repo: repo **Settings › General › Transfer ownership**.
- Then each person gets a role: **Read** (can download / clone, can't change), **Triage**, **Write** (can push
  branches and merge), **Maintain**, **Admin**.
- Forks of private repos in an organization are **off by default**: turn on *Settings › Member privileges ›
  Allow forking of private repositories* for the org, and *Allow forking* on the repo, if you want people to work in forks.
- Rule of thumb: most of the team = Read (or no GitHub at all, just the zip); 1–2 people = Write/Maintain; you = Admin.

### Protecting the main branch
Branch protection (requiring a pull request + your review before anything lands on `main`) is **not available for
private repos on free GitHub plans**: it needs GitHub Pro (personal) or GitHub Team (organization). On a free
plan, the working agreement is: everyone except the maintainer works on a branch and opens a pull request;
the maintainer merges.

## 3. The shoot server
BB Takes only reads the server. Access to footage is whatever each person's server login allows; sharing the
tool doesn't change that.

## Checklist for adding a teammate
- [ ] Send them the latest zip (everyone).
- [ ] Make sure they can mount the shoot server.
- [ ] Only if they'll change the code: invite them to the GitHub repo (and, in an org, pick their role).
