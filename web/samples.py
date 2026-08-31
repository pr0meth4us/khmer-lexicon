"""Preloaded drafts, so a reviewer can click once instead of typing Khmer.

Each one is written to exercise a different part of the checker. Terms were
picked by checking membership in dist/unified_lexicon.json first, so the
positive signal is real and not staged text that happens to look plausible.
"""

SAMPLES = [
    {
        "name": "សេចក្ដីជូនដំណឹង",
        "note": "Ordinary approved terminology. Everything highlighted here is "
                "an official term with a ministry and a year behind it.",
        "text": (
            "រដ្ឋាភិបាល បានអនុម័តលើគោលនយោបាយស្តីពីបរិវត្តកម្មឌីជីថល "
            "ដើម្បីពង្រឹងអភិបាលកិច្ច និងការគ្រប់គ្រងទិន្នន័យ។ "
            "ក្រសួងនឹងសហការជាមួយវិស័យឯកជន ក្នុងការអភិវឌ្ឍព័ត៌មានវិទ្យា "
            "និងទូរគមនាគមន៍ ទូទាំងប្រទេស។"
        ),
    },
    {
        "name": "លិខិតមានពាក្យអង់គ្លេស",
        "note": "The same letter written the way drafts actually arrive — with "
                "English left in place. Each loanword has an approved Khmer "
                "rendering in the lexicon, offered as a replacement.",
        "text": (
            "ក្រសួងនឹងរៀបចំផែនការសម្រាប់ digital transformation "
            "ក្នុងឆ្នាំ២០២៦។ ការគ្រប់គ្រង data នឹងធ្វើឡើងតាមស្តង់ដារជាតិ "
            "ហើយ governance របស់ប្រព័ន្ធនឹងស្ថិតនៅក្រោមការត្រួតពិនិត្យ "
            "របស់រដ្ឋាភិបាល។ policy ថ្មីនឹងអនុវត្តចាប់ពីត្រីមាសទី១។"
        ),
    },
    {
        "name": "អត្ថបទមានតួអក្សរខុស",
        "note": "Looks identical to correct Khmer on screen. Contains a "
                "Devanagari vowel sign, a Thai vowel and a Cyrillic letter — "
                "invisible to a reader, fatal to search, sort and dedup.",
        "text": (
            "សេចក្ដीប្រកាសរបស់រដ្ឋាភិបាល ស្តីពីការគ្រប់គ្រងទិន្នន័យ "
            "និងអភិបាលកិច្ចឌីជីថល។ ឯកសារយោង៖ aquñşıyшn "
            "ត្រូវបានផ្ទៀងផ្ទាត់ដោយក្រុមការងារបច្ចេកទេស។"
        ),
    },
    {
        "name": "អត្ថបទរដ្ឋបាល",
        "note": "Short lexicon terms sit inside longer, unrelated words here. "
                "A plain dictionary scan reports them; the cluster and word "
                "boundary filters throw them out. Open the rejected list.",
        "text": (
            "អគ្គនាយកដ្ឋានបានប្រកាសអំពីយុទ្ធសាស្ត្របញ្ចកោណ "
            "និងកិច្ចសន្យាដែលបានចុះហត្ថលេខារួច។ "
            "សេចក្តីសម្រេចនេះនឹងចូលជាធរមាននៅថ្ងៃទី១ ខែមករា។"
        ),
    },
]
