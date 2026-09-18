# DVC Workflow Documentation

## Remote Storage
- Remote name: `myremote`
- Type: Local folder (simulating shared/cloud storage for classroom use)
- Path: `~/dvc-remote-storage`
- Configured as default remote using: `dvc remote add -d myremote ~/dvc-remote-storage`

## Data Versioning Cycle
For every dataset change, the following cycle was followed:
1. `dvc add data/raw/iris_v1.csv` — track dataset content, generate/update `.dvc` metafile
2. `git add data/raw/iris_v1.csv.dvc` — stage the metafile (not the data itself)
3. `git commit -m "..."` — record the dataset version pointer in Git history
4. `dvc push` — upload the actual data object to the DVC remote

## Dataset Versions Tracked
| Version | Git Commit | Rows | MD5 Hash |
|---------|-----------|------|----------|
| v1 | b36a975 | 150 | 21d441a28bce4417276097df955afc50 |
| v2 | c59bbef | 170 | 674c8c36bb7c4ba8d851dee9e6ee67af |

## Comparing and Restoring Versions
- `dvc diff b36a975` — compared current working data against Version 1, confirmed `data/raw/iris_v1.csv` as Modified.
- `git checkout <commit> -- data/raw/iris_v1.csv.dvc` followed by `dvc checkout data/raw/iris_v1.csv.dvc` — restored the exact historical dataset (151 lines for v1, 171 lines for v2) on demand.

## Conclusion
This confirms DVC + Git together provide full reproducibility: any historical commit can be checked out to retrieve the exact code and data pair used at that point in the project.