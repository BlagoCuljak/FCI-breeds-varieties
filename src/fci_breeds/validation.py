from .models import Snapshot, Variety


def leaves(varieties: list[Variety]):
    for variety in varieties:
        if variety.subvarieties:
            yield from leaves(variety.subvarieties)
        else:
            yield variety


def counts(snapshot: Snapshot) -> dict[str, int]:
    return {
        "breeds": len(snapshot.breeds),
        "definitive": sum(b.recognition_status == "definitive" for b in snapshot.breeds),
        "provisional": sum(b.recognition_status == "provisional" for b in snapshot.breeds),
        "varieties": sum(len(b.varieties) for b in snapshot.breeds),
        "leaves": sum(len(list(leaves(b.varieties))) or 1 for b in snapshot.breeds),
    }


def validate(snapshot: Snapshot, previous: Snapshot | None = None) -> None:
    ids = [b.fci_id for b in snapshot.breeds]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate breed IDs")
    if len(ids) < 300:
        raise ValueError(f"Incomplete catalogue: only {len(ids)} breeds")
    if {b.group for b in snapshot.breeds} != set(range(1, 11)):
        raise ValueError("Catalogue must contain all ten groups and no missing groups")
    if not any(b.recognition_status == "provisional" for b in snapshot.breeds):
        raise ValueError("Missing provisional breeds")
    for breed in snapshot.breeds:
        if not breed.english_name:
            raise ValueError(f"Missing English name for {breed.fci_id}")
        codes = [v.code for v in breed.varieties]
        if len(codes) != len(set(codes)):
            raise ValueError(f"Duplicate variety codes for {breed.fci_id}")
        if breed.recognition_status == "provisional":
            if breed.cacib_group_id or any(v.cacib_group_id for v in leaves(breed.varieties)):
                raise ValueError(f"Provisional breed {breed.fci_id} has a CACIB award")
    by_id = {b.fci_id: b for b in snapshot.breeds}
    for fci_id, expected in {172: 4, 148: 3, 15: 4, 218: 2}.items():
        if fci_id not in by_id or len(by_id[fci_id].varieties) != expected:
            raise ValueError(f"Unexpected variety structure for reference breed {fci_id}")
    if len(list(leaves(by_id[148].varieties))) != 9:
        raise ValueError("Expected nine Dachshund size/coat combinations")
    if previous:
        old, new = counts(previous), counts(snapshot)
        for key in ("breeds", "varieties", "leaves"):
            if new[key] < old[key] * 0.95:
                raise ValueError(f"{key} dropped by more than 5%: {old[key]} -> {new[key]}")
        old_ids = {b.fci_id for b in previous.breeds}
        if len(old_ids - set(ids)) > max(1, len(old_ids) * 0.02):
            raise ValueError("More than 2% of previously published breed IDs disappeared")
