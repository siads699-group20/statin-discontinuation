# MEPS data sources

The pipeline downloads only the public-use files listed here. The downloaded
ZIP archives are kept unchanged in `data/raw/`, which is Git-ignored.

From the repository root, run:

```powershell
python src/download_meps.py
```

| File | Description | Download URL | Codebook |
|---|---|---|---|
| `h252dta.zip` | Longitudinal file, Panel 27 (2022-23); person and five-round follow-up data | <https://meps.ahrq.gov/mepsweb/data_files/pufs/h252/h252dta.zip> | <https://meps.ahrq.gov/data_stats/download_data/pufs/h252/h252cb.pdf> |
| `h239adta.zip` | Prescribed medicines file (2022) | <https://meps.ahrq.gov/mepsweb/data_files/pufs/h239a/h239adta.zip> | <https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_codebook.jsp?PUFId=H239A> |
| `h248adta.zip` | Prescribed medicines file (2023) | <https://meps.ahrq.gov/mepsweb/data_files/pufs/h248a/h248adta.zip> | <https://meps.ahrq.gov/mepsweb/data_stats/download_data/pufs/h248a/h248acb.pdf> |
| `h241dta.zip` | Medical conditions file (2022) | <https://meps.ahrq.gov/mepsweb/data_files/pufs/h241/h241dta.zip> | <https://meps.ahrq.gov/mepsweb/data_stats/download_data_files_codebook.jsp?PUFId=H241> |
| `h249dta.zip` | Medical conditions file (2023) | <https://meps.ahrq.gov/mepsweb/data_files/pufs/h249/h249dta.zip> | <https://meps.ahrq.gov/mepsweb/data_stats/download_data/pufs/h249/h249cb.pdf> |

These annual files include other panels where applicable. Filter annual records
to Panel 27 when preparing the study data. Panel 27 round 3
appears in 2022 and 2023 (round three occurs in both)
