# Third-party materials

The `vendor/` directory contains verbatim copies of selected upstream files.
`upstream.lock` identifies their source repositories, commits, paths and hashes.
The upstream terms and notices control those files.

- **RTK:** Apache-2.0-licensed awareness text, with the upstream license in
  `vendor/rtk/`. No RTK binary, engine or proxy is distributed in this repository.
  Supported RTK binary pins refer only to the Apache-2.0 OSS edition.
- **Headroom:** The upstream Apache-2.0 license and notice are in
  `vendor/headroom/`. No Headroom runtime is bundled.
- **Caveman:** Upstream license, MIT legacy notice, notices, licensing details
  and trademark guidance are in `vendor/caveman/`. Only the listed skill text
  is bundled; this repository is not a Caveman product or distribution.
- **Ponytail:** The upstream MIT license is in `vendor/ponytail/`.

The installer generates adapted RTK, Caveman and Ponytail guidance from
some of these upstream files. The generated copies identify their origin
and changes; the vendored originals are unchanged.
