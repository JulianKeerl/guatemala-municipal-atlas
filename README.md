# Guatemala Municipial Atlas

Interactive maps of development indicators for Guatemala


**Status**: WIP

## Why

Development data for Guatemala is mostly published in long PDF reports. This project turns this data into maps, that show per municipality, where things stand and how they have changed over time. 

The first indicator this project is focussed on is chronic malnutrition among first-graders. Reports are from 1986, 2001, 2008, 2015 and 2024. 

## Data sources

| Date | Source | Comment |
|---|---|---|
| 2008 | [Censo de Talla 2008](https://portal.siinsan.gob.gt/wp-content/uploads/Tercer-censo-nacional-de-talla-2008.pdf) |  Also contains 2001 |
| 2015 | [Censo de Talla 2015](https://portal.siinsan.gob.gt/wp-content/uploads/Informe-Censo-de-Talla-en-Escolares-Guatemala-2015.pdf) |Also contains 1986–2008 |
| 2024 | [Censo Nacional de Talla en Escolares 2024](https://portal.siinsan.gob.gt/archivos/censo_02.pdf) | Also contains 1986–2024 |


These reports are not stored in this repository. Download them into `data/raw` to run the pipeline.

## Roadmap

- [ ] Chronic malnutrition, 1986–2024
- [ ] More indicators, such as poverty, basic services and violence

## License

[MIT](LICENSE)