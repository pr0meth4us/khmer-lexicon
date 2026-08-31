"""Self-check for khmerlex. Run: python3 test_khmerlex.py"""
from khmerlex import boundaries, cluster_len, clusters, edit_distance, on_boundary


def test_coeng_binds_the_following_consonant():
    # ក ្ រ ស ួ ង -- 6 code points, 3 clusters. Code-point slicing at 1 or 2
    # would leave a bare COENG, which renders as a stray mark and matches nothing.
    assert clusters("ក្រសួង") == ["ក្រ", "សួ", "ង"]
    assert len("ក្រសួង") == 6 and cluster_len("ក្រសួង") == 3
    assert clusters("ស្ត្រី") == ["ស្ត្រី"]          # two stacked coeng, one cluster
    assert clusters("សេចក្ដី") == ["សេ", "ច", "ក្ដី"]  # marks attach to their base


def test_boundaries_reject_mid_cluster_offsets():
    text = "ក្រសួង"
    assert boundaries(text) == {0, 3, 5, 6}
    assert on_boundary(text, 0, 3)          # exactly ក្រ
    assert not on_boundary(text, 0, 1)      # splits ក from its coeng
    assert not on_boundary(text, 1, 3)      # starts on a bare coeng


def test_edit_distance_counts_clusters_not_code_points():
    # Same base, one differing vowel: 1 cluster apart, but 1 code point too --
    # the interesting case is where they disagree.
    assert edit_distance("ក្រសួង", "ក្រសួង") == 0
    # ក្រសួង is 3 clusters, ក្រសួងការ is 5 (ការ is កា + រ): two added.
    assert edit_distance("ក្រសួង", "ក្រសួងការ") == 2
    # 4 code points differ, but only 2 clusters do.
    assert edit_distance("សេវាកម្ម", "សេវា") == 2
    # A real mark-order defect from the lexicon: ភ្ជាប់ ("attach") written with
    # the vowel before the coeng. Identical code points, different order --
    # 0 apart under NFC, 2 clusters apart here, and the clustering shows why:
    # ភ្ជាប់ is ['ភ្ជា', 'ប់'] but ភា្ជប់ is ['ភា្', 'ជ', 'ប់'], a dangling coeng.
    assert edit_distance("ភ្ជាប់", "ភា្ជប់") == 2


def test_cutoff_short_circuits():
    long_a, long_b = "ក្រសួង" * 8, "បញ្ចកោណ" * 8
    assert edit_distance(long_a, long_b, cutoff=1) == 2      # "> 1", reported as cutoff+1
    assert edit_distance("ក្រសួង", "ក្រសួង", cutoff=1) == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all khmerlex checks passed")
