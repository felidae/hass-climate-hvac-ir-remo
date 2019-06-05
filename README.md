Home Assistant platform for Nature Remo Local API
==========

Home Assistant platform for Nature Remo Local API.

It works as climate component, and synthes HVAC IR signal.

## Notice and Limitations

- This is just Proof of Concept, use only TESTING. I told you.
- This is UNOFFICIAL.
  - No permittion from
    - HVAC vendor
    - python library creator
    - original sample code creator
- I test it on hass.io on Docker.

## How to try

- Place files which this repository contains into your hass's `custom_components/hvac_ir` folder.
- Get HVAC model type from here. -> `https://github.com/shprota/hvac_ir/tree/master/hvac_ir`
  - e.g. daikin2, fujitsu
- Add config to `configuration.yaml`.

```
climate:
  - platform: hvac_ir
    name: Set your HVAC name.
    host: <Nature Remo IP>
    type: <HVAC model type>

```
- Restart hass.
