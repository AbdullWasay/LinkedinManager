from app.integrations.job_sources.arbeitnow import ArbeitnowAdapter
from app.integrations.job_sources.cold_website import ColdWebsiteAdapter
from app.integrations.job_sources.curated_research import CuratedResearchAdapter
from app.integrations.job_sources.email_page_watch import EmailPageWatchAdapter
from app.integrations.job_sources.jobicy import JobicyAdapter
from app.integrations.job_sources.linkedin_posters import LinkedInPosterAdapter
from app.integrations.job_sources.remoteok import RemoteOKAdapter
from app.integrations.job_sources.remotive import RemotiveAdapter
from app.integrations.job_sources.startup_outreach import StartupOutreachAdapter

# Authenticity + freshness gates live in discovery ingest.
# Boards are allowed again only when they yield a real email and are ≤7 days old.
DEFAULT_ADAPTERS = [
    StartupOutreachAdapter(),
    ColdWebsiteAdapter(),
    EmailPageWatchAdapter(),
    LinkedInPosterAdapter(),
    CuratedResearchAdapter(),
    RemoteOKAdapter(),
    RemotiveAdapter(),
    JobicyAdapter(),
    ArbeitnowAdapter(),
]

EMAIL_FIRST_ADAPTERS = [
    StartupOutreachAdapter(),
    ColdWebsiteAdapter(),
    EmailPageWatchAdapter(),
    LinkedInPosterAdapter(),
    RemoteOKAdapter(),
    RemotiveAdapter(),
    JobicyAdapter(),
    ArbeitnowAdapter(),
    CuratedResearchAdapter(),
]
