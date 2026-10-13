FOUNDER OUTREACH ASSISTANT

A python based application for discovering relevant company founders, ranking prospects against defined criteria, preparing personalized LinkedIn outreach drafts and tracking outreach activity.

The project is being developed incrementally using Python and FastAPI, with an emphasis on growing backend development expertise and building a maintanable application.

Project Goals

• Discover potential founder prospects through an authorised professional-data API.
• Filter and rank prospects according to defined criteria.
• Save selected founder profiles according to defined criteria.
• Generate personalised outreach message drafts using available profile and company information.
• Track outreach activity, including invitations and replies.
• Provde a simple interface for managing prospects.

PLANNED TECHNOLOGY STACK

Backend

•Python (handles all backend)
•FastAPI (application by which we make requests to the server)
•Pydantic (data validation and parsing)
•SQLAlchemy (database bridge)
•Alembic (monitors migrations)
• PostreSQL (database)

Frontend

•React
•TypeScript
•Tailwind CSS

Testing and Development

•Pytest
•Docker
•Docker Compose
•Git

External Data Provider

Initial provider: DDGS web search library

the initial protoytpe uses the ddgs python package to discover publicly available web pages related to founders and companies.

Search results provide titles, URLs, and snippets. The application will filter and rank results before presenting them for review.

DDGS is an unofficial metasearch library, not dedicated professional-data API. search availabilty, rate limits, and result quality may vary.

Contraints
•No paid API subscription or bank card is required for the initial prototype
•Validate search results before treating them as founder records
•Do not assume a search result proves a person's role or current employment.
•Don not scarpe restricted profile pages or automate LinkedIn invitations
• Keep the search provider isolated so it can be replaced later


ARCHITECTURE

The application will use a frontend-backend architecture.

1. Frontend: Allows the user to enter search criteria, review prospects, edit message drafts, and track outreach.
2. Backend: Handles requests, validates data, applies ranking rules, generates message drafts, and coordinates data storage.
3. Database: Stores founder records, search history, outreach drafts, and activity statuses.
4. External data provider: Supplies professional profile and company information through an authorised API.

The frontend communicates with the backend through HTTP requests and JSON responses.The backend communicates with the database and external provider when needed.

PLANNED WORKFLOW

1. Enter founder search criteria
2. Retrieve matching profiles from the data provider.
3. Rank prospects using transparent. configurable rules.
4. Review and save selected prospects.
5. Generate personalised outreach drafts.
6. Open profiles and send outreach manually.
7. Record invitations, acceptances, replies, and follow-up activity.

The intial version will not automatically scrape or send connection requests.

PROJECT STATUS

Current stage: Initial backend setup

☑️Create the project directory
☑️Create and activate a python virtual environment
☑️Install FastAPI
☑️Create the initial FastAPI application
☑️Run the development server and verify the application
Define and validate founder data
Implement founder-related API endpoints.
Add Persistant database storage.
Integrate an authorised professional-data API.
Build the frontend.
Add tests and containerized deployment.

DEVELOPMENT PRINCIPLES

•Build incrementally and explain the purpose of each component.
•Keep business logic separate from API routes and database access.
•Validate incoming data
•Write tests for important functionality.
•Keep API credentials and other secrets out of source control
•Respect external providers' terms and applicable privacy requirements.

LICENSE

No license has been selected yet.
