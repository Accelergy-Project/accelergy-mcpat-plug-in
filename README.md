# McPAT Plug-in for Accelergy

An energy estimation plug-in for [Accelergy framework](https://github.com/nelliewu95/accelergy). It is a wrapper for
the McPAT integrated power, area, and timing framework. It works by substituting in attributes to the `properties.xml`
definition file, running McPAT, and parsing the output. Since queries to McPAT can take some time, results are cached
in the file `.cache` so repeated invocations are not repeated. To clear the cache delete the `.cache` file.

## Get started 
- Install [Accelergy framework](https://github.com/nelliewu95/accelergy)
- Download and build [McPat 1.3](https://github.com/HewlettPackard/mcpat) 

## Use the plug-in
- Clone the repo by ```git clone https://github.com/Accelergy-Project/accelergy-mcpat-plug-in.git```
- To set the relative accuracy of your McPat plug-in
    - open ```mcpat_wrapper.py``` 
    - Edit the first line to set the ```MCPAT_ACCURACY``` (default is 80)
- Option 1
    - Run ```pip3 install .``` and use the same arguments as installing Accelergy 
- Option 2
    - Open Accelergy's config file ```accelergy_config.yaml``` and add a new list item that points to the cloned folder
- Place the built McPat
    - Inside the installed McPat plug-in folder if you choose option 1 above/cloned McPat folder if you choose option2 above (or its subfolder)
    - Inside any folder (or its subfolder) that is included in the ```$PATH```
- Run Accelergy (Accelergy's log will show that it identifies the McPat plug-in )

## Supported components
- Branch predictor `tournament_bp`
- Branch target buffer `btb`
- Cache `cache`
- Crossbar `xbar`
- Decoder `decoder`
- Fetch buffer `fetch_buffer`
- Functional unit `func_unit`
- Instruction queue `inst_queue`
- Load store queue `load_store_queue`
- Register file `cpu_regfile`
- Renaming unit `renaming_unit`
- Reorder buffer `reorder_buffer`
- Translation lookaside buffer `tlb`
