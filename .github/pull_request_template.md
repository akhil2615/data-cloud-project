## Kit

- Space:
- Kit name (`DK<layer>_<scope>_<space>_v<n>`):
- Fresh version (not an edit of the previous kit XML):

## Four-eyes review

- [ ] Manifest was downloaded from the Data Kit UI
- [ ] View/Add Dependencies was run, and the publish sequence was checked
- [ ] `cleanup-kit.sh` was run
- [ ] This space's order in `kit-matrix.yaml` is correct, including step 10c if the transform needs identity resolution, insights, segments, or activation DMOs
- [ ] No secrets, connector passwords, or `KQ_*` fields

Two approvals are required before merge to `release`.
