# HomeboxLabel

HomeboxLabel is a small external label-rendering service for [Homebox](https://github.com/sysadminsmedia/homebox). It was created to keep compact item labels while generating larger, tote-friendly **4 × 6 inch landscape labels** for Homebox locations.

The service accepts Homebox's external label-maker request, generates a PNG label, and returns it directly to Homebox.

## What it does

- Generates **4 × 6 inch landscape location labels** at 1800 × 1200 pixels / 300 DPI.
- Keeps item labels compact by using the width and height supplied by Homebox.
- Generates scannable QR codes pointing back to the Homebox item or location.
- Repairs relative Homebox QR paths using `PUBLIC_BASE_URL`.
- Wraps long location names and secondary text to a maximum of two lines, shrinking text when necessary and adding an ellipsis only as a last resort.
- Suppresses generic filler such as `Location`, `Homebox Location`, `Item`, and `Homebox Item` from secondary text.
- Runs as a lightweight Docker container and is suitable for Unraid.

## Container image

GitHub Actions builds and publishes the container to GitHub Container Registry:

```text
ghcr.io/kevinatlee/homeboxlabel:latest
```

The published image targets `linux/amd64`.

## Unraid setup

HomeboxLabel includes an Unraid Community Apps template under `templates/homeboxlabel.xml`. Once the project is accepted into Community Apps, install it from the Apps tab and provide the public base URL of your Homebox instance when prompted.

For a manual Unraid install, create a Docker container using:

```text
Repository: ghcr.io/kevinatlee/homeboxlabel:latest
```

The application listens on container port `8787`. The host port can be any unused port. For example:

```text
Host port:      9797
Container port: 8787
```

Add the following environment variable to the HomeboxLabel container, replacing the example with your own Homebox URL:

```text
PUBLIC_BASE_URL=https://homebox.example.com
```

`PUBLIC_BASE_URL` is used when Homebox sends a relative QR target such as `/location/<id>`. The service converts it to a complete URL before generating the QR code.

### Homebox configuration

Point Homebox's external label maker at HomeboxLabel:

```text
HBOX_LABEL_MAKER_LABEL_SERVICE_URL=http://<UNRAID-IP>:9797/
HBOX_LABEL_MAKER_LABEL_SERVICE_TIMEOUT=30s
```

Restart Homebox after changing these variables.

## Label behavior

### Locations

HomeboxLabel identifies location requests from the URL supplied by Homebox. Location labels are rendered at a fixed 4 × 6 inch landscape size:

```text
1800 × 1200 pixels
300 DPI
```

The QR code is placed on the left and the location text is centered in the remaining space. Long title and secondary fields wrap to two lines and automatically reduce font size as needed.

### Items

Requests that are not identified as locations use the `Width` and `Height` values supplied by Homebox, preserving the smaller item-label workflow.

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `PUBLIC_BASE_URL` | Recommended | empty | Public Homebox base URL used to convert relative QR paths into complete URLs. |
| `PORT` | No | `8787` | TCP port HomeboxLabel listens on inside the container. |

## Community Apps repository metadata

The repository contains the files required by the current Unraid Community Apps repository submission flow:

- `LICENSE` — MIT license for the repository contents.
- `ca_profile.xml` — Community Apps repository profile and support metadata.
- `icon.svg` — project icon used by the repository profile and app template.
- `templates/homeboxlabel.xml` — Unraid Docker application template.

## Local build

```bash
docker build -t homeboxlabel:local .
```

Run it with:

```bash
docker run -d \
  --name HomeboxLabel \
  -p 9797:8787 \
  -e PUBLIC_BASE_URL=https://homebox.example.com \
  homeboxlabel:local
```

## Publishing

Pushes to `main` automatically build and publish:

```text
ghcr.io/kevinatlee/homeboxlabel:latest
```

Version tags matching `v*.*.*` are also published. For example, Git tag `v1.0.0` produces an image tagged `v1.0.0` in GHCR.

Pull requests build the Docker image for validation but do not publish it.

## License

HomeboxLabel is available under the MIT License. See `LICENSE` for details.

## Project status

HomeboxLabel is a small purpose-built companion service and is not affiliated with or maintained by the Homebox project.
