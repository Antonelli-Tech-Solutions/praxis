const GITLAB_REPO_URL = "https://labs.gauntletai.com/monicapeters/praxis";

export function GitLabRepoLink() {
  return (
    <a
      className="gitlab-repo-link"
      href={GITLAB_REPO_URL}
      target="_blank"
      rel="noreferrer noopener"
      aria-label="View PRAXIS repository on GitLab"
      title="PRAXIS on GitLab"
    >
      <svg
        className="gitlab-repo-link__icon"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        focusable="false"
      >
        <path
          fill="currentColor"
          d="M23.955 9.592h-.006L20.893.497a.751.751 0 0 0-.753-.497h-3.28l-1.203 3.684H7.343L6.14.0h-3.28a.751.751 0 0 0-.753.497L.051 9.592a.75.75 0 0 0 .271.825l10.68 7.776-4.204-12.87L12 9.592l5.202 5.701-4.204 12.87 10.68-7.776a.75.75 0 0 0 .279-.805z"
        />
      </svg>
    </a>
  );
}
