"""Run independent base/optional encodes, then verify each real bitstream."""
from concurrent.futures import ThreadPoolExecutor
from run_encode import run as encode
from verify import run as verify
from check_border import run as border

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(encode,extended) for extended in (False,True)]
        for future in futures:future.result()
    verify(False)
    verify(True)
    border()
