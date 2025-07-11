# Multi-value

Multi-values on a tag is useful to provide different and independent information
belonging to the same context.

This plugin:
- Add a command to add/remove values in a multi-value tag
- Fix `grouping` field and add `work` field (Optional)

## Beet official list tags

A few fields already support native multivalue separated with `\␀`. Those are
always available in the command without configuration change. The current fields
are:

- artists
- albumartists
- artists_sort
- artists_credit
- albumartists_sort
- albumartists_credit
- mb_artistids
- mb_albumartistids

## String multi-value tags

Some fields do not support multi-values yet like
[genre](https://github.com/beetbox/beets/pull/5426) or some may never support it
as not a "standard" like `grouping`.

An example could be to add multiple genres separated by a comma: `Rock,Hard Rock`

Some external tools also supports custom separator splitting like
[navidrome](https://www.navidrome.org/docs/usage/customtags/#changing-separators)
since v0.55.0.

By default, no field is considered a string multi-value. Each one must be
explicitly defined in the configuration with the requested separator:

```yaml
multivalue:
  string_fields:
    grouping: ";"
    genre: ","
```

# Searching

```shell
# Non overlapping with usual
beet ls genre:[]Rock # equals to genre:Rock
# Regex search
# Under the hood `.` is transformed to `[^<sep>]
# And ^$, to look fo the real start/end or the separator
beet ls genre:[]:Rock
# Enforce full match by looking for the separator or the start/end
beet ls genre:[]=Rock
beet ls genre:[]=~Rock

beet ls genre:[]#Rock

# Multi-search
beet ls genre:[]{Rock,:Class?ic} # At least one of the value
beet ls genre:[][Rock,:Class?ic] # All the values must be present

# "," delimits the values, to use a "," in the string "\,"
```

For all searches, if the separator is present in the query, a warning is printed
but the query is still run. It may even be a false positive in the case of the
regex case: `genre:[]:[a-z]{3,9}`. The comma is part of the regex syntax, but
the warning is always added.


# Modify Command

It is possible to add or remove value:

```shell
# genre: Rock
beet multivalue grouping+="Hard Rock" <query>
# genre: Rock,Hard Rock
beet multi genre+="Classic Rock" genre-="Hard Rock" genre-="Blues" <query>
# genre: Rock,Classic Rock
```

TODO: Full set genre=[,,]

The command is heavily influenced by the modify one and provide the same flags.
By default, a confirmation after showing the diff is requested.

The diff may be sub-optimal as it does not know about the separator, like
`genre: Hard Rock,**Classic** Rock,**Rock** -> Hard Rock,Rock`. But the apply
change is still accurate.

To clear a multi-value field, the original modify command still applies:

```shell
beet modify mv-field!
```

# Grouping/Work fields

https://github.com/beetbox/mediafile/issues/15 `mediafile` the file level
library is using the wrong tag name for MP3. As a result, the common work is
visible. As grouping field was my first motivation to use string multi-value,
this plugin is also able to fix the field.

In such case:
- `grouping`: for MP3 is `GRP1` and ASF is removed as without a value
- `work` field is added for MP3 (`TIT1`), MP4 (`@wrk`), Vorbis (`WORK`) and ASF
  (`WM/ContentGroupDescription`). The value for MP3 and ASF was previously
  assigned to `grouping`.

The tags are chosen from [Kid3
table](https://kid3.sourceforge.io/kid3_en.html#frame-list).

To enable it:

```yaml
multivalue:
  fix_media_fields: true
```

It is required to make beets read the tags from the file again as else the kept
value in DB is the old one from a potential wrong fields:

```shell
beet update -F work -F grouping
```

WARNING: As the work was not saved to the file previously, by reading from the
files it may remove all the "work" fetched from Musicbrainz and only stored in
the DB.

