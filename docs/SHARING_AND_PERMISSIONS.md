# Sharing BB Takes and who gets access

There are two separate things to share:

1. **The tool itself**: the zip. Everyone who uses BB Takes needs this. No GitHub account needed.
2. **The GitHub repo**: public (anyone can read and download it). Only people you add as collaborators can change it.

## 1. Sharing the zip (everyone)
- The maintainer builds it with `bash scripts/make_release.sh` → `dist/BB_Takes_vX.Y.Z.zip` (≈ 57 MB, includes ffmpeg).
- Share it the way the team already shares files: Slack/WhatsApp, Google Drive, or a `Tools` folder on the
  shoot server. (Claude can't write to the server, so a person with write access copies it there.)
- People unzip it and follow `docs/SETUP.md`. When there's a new version, they replace the folder; their exports
  and previews are kept.

## 2. The GitHub repo (maintainers)

### Who can see it
The repo is **public**: anyone can view, clone, download the release zip and fork it. Nobody can change it except
the owner and invited collaborators; anyone else can only suggest changes through a pull request from their fork.
The team password gate (`server/gate.py`) is a light check, not protection for what's in the repo.

### Inviting someone
GitHub › the `bb-takes` repo › **Settings › Collaborators** › **Add people** › their GitHub username or email.
They get an email invite and must accept it. Remove them from the same page at any time.

Or from Terminal: `gh api -X PUT repos/<owner>/bb-takes/collaborators/<their-username> -f permission=push`

### What they can do: depends on where the repo lives
**On your personal account (simplest, what we start with):**
- Personal repos have only one level for invitees: **collaborator = read + write** (they can push changes).
- Anyone can **fork** a public repo and open a pull request; only collaborators can merge or push.
- Good for a small group of trusted people who'll actually change the code.

**In a GitHub Organization (when you want finer control):**
- Create a free organization (GitHub › your avatar › Your organizations › New organization › Free), e.g. `bb-team`,
  then transfer the repo: repo **Settings › General › Transfer ownership**.
- Then each person gets a role: **Read** (can download / clone, can't change), **Triage**, **Write** (can push
  branches and merge), **Maintain**, **Admin**.
- Rule of thumb: most of the team = Read (or no GitHub at all, just the zip); 1–2 people = Write/Maintain; you = Admin.

### Protecting the main branch
Public repos can use branch protection on the free plan: repo **Settings › Branches › Add rule** for `main` →
"Require a pull request before merging" (+ required approvals). Then even collaborators go through a reviewed PR.

## 3. The shoot server
BB Takes only reads the server. Access to footage is whatever each person's server login allows; sharing the
tool doesn't change that.

## Checklist for adding a teammate
- [ ] Send them the latest zip (everyone).
- [ ] Make sure they can mount the shoot server.
- [ ] Only if they'll change the code: invite them to the GitHub repo (and, in an org, pick their role).
