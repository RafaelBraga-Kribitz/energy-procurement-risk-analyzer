# Azure deployment path (ADR-020)

**Status: Azure-ready, deployment path documented — not deployed.** The
pipeline runs entirely locally / in CI on DuckDB. This guide adds an optional
cloud copy of the results: raw parquet + Power BI exports in **Azure Blob
Storage**, and every export table in **Azure SQL Database** (so Power BI can
also connect to SQL instead of CSV). Nothing below is needed to run the project.

## What gets created (`infra/azure/main.bicep`)

| Resource | SKU | Why |
|---|---|---|
| Storage account + private container `epra` | Standard_LRS, Hot | `raw/…` parquet, `exports/<run_id>/…` and `exports/latest/…` CSVs |
| Azure SQL logical server | — | hosts the database, TLS 1.2 |
| Azure SQL database `epra` | General Purpose serverless `GP_S_Gen5_2`, **free offer** (`useFreeLimit: true`, `freeLimitExhaustionBehavior: AutoPause`) | schema `epra`, one table per export |
| Firewall rules | — | Azure services (optional) + your client IP |

## Cost note (target: EUR 0)

- **Azure SQL free offer:** at the time of writing Microsoft offers a monthly
  free allowance of vCore seconds and storage per subscription for serverless
  General Purpose databases. With `AutoPause` as the exhaustion behaviour the
  database **pauses instead of billing** once the allowance is used. A
  once-a-month refresh plus occasional Power BI refreshes stays far inside it.
  Check the current terms on the Azure portal before deploying — offers change.
- **Blob Storage is not free:** Standard_LRS storage and transactions bill per
  GB and per 10,000 operations. The full raw + exports footprint is tens of MB,
  i.e. cents per month — not zero. A new Azure account's trial credit covers it.
- Risks of charges: switching `freeLimitExhaustionBehavior` to `BillOverUsage`,
  creating a second database outside the free offer, or leaving a large client
  IP range open. Delete the resource group to stop all cost.

## Steps

1. Azure CLI login and resource group:
   ```bash
   az login
   az group create -n rg-epra -l westeurope
   ```
2. Deploy (password typed at the prompt, never committed):
   ```bash
   az deployment group create -g rg-epra -f infra/azure/main.bicep \
     -p sqlAdminLogin=epra_admin clientIp=$(curl -s https://ifconfig.me) \
     -p sqlAdminPassword
   ```
   Outputs: storage account name, blob endpoint, SQL server FQDN, database name.
3. Local run against Azure:
   ```bash
   uv sync --extra dev --extra azure          # azure-storage-blob, azure-identity, pyodbc
   # Microsoft ODBC Driver 18 for SQL Server must be installed on the machine.
   export AZURE_STORAGE_CONNECTION_STRING="..."   # from: az storage account show-connection-string
   export AZURE_SQL_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=tcp:<fqdn>,1433;Database=epra;Uid=epra_admin;Pwd=...;Encrypt=yes;"
   make all                 # local pipeline (DuckDB), unchanged
   make publish TARGET=azure
   ```
   Instead of the storage connection string you can set
   `AZURE_STORAGE_ACCOUNT_URL` and sign in with Entra ID (`DefaultAzureCredential`).
4. Scheduled run: add `AZURE_STORAGE_CONNECTION_STRING` and
   `AZURE_SQL_CONNECTION_STRING` as **GitHub Actions secrets**. The monthly
   workflow (`.github/workflows/refresh.yml`) then publishes after each refresh;
   without them it skips the Azure step. The ODBC driver is preinstalled on
   GitHub's `ubuntu-latest` runners.
5. Power BI on Azure SQL (optional): *Get data → Azure SQL database* → server
   FQDN, database `epra`, tables `epra.*` — same names and columns as the CSVs,
   so `dashboards/measures.dax` works unchanged.

## How the code is organised

- `src/epra/cloud/targets.py` — `PublishTarget` protocol, `LocalTarget`,
  `AzureTarget` (Blob upload; create-if-missing + truncate + bulk insert in one
  transaction, rollback on error). Clients are injected; Azure SDK and ODBC are
  imported only on the Azure path.
- `tests/unit/test_cloud.py` — fakes for Blob and SQL; no network, no SDK.
- Secrets: env vars / GitHub secrets only (EN-041, A-7). Nothing in YAML.

## Not done here (human actions)

- No Azure subscription was available to the build session, so the Bicep
  template was written but **not deployed or compiled** (`az bicep build`
  was not available). Run `az bicep build -f infra/azure/main.bicep` first.
- When a real deployment run exists, record it in `docs/BUILD_LOG.md`; only
  then may the README say the results are published on Azure.
