''' functions tu use matplotib styles '''

import pathlib

here = pathlib.Path(__file__).parent
plt_styles_dir = here / 'plotting_styles'
darkstyle = (
    plt_styles_dir / 'dark.mplstyle',
)

notebookstyle = (
    plt_styles_dir / 'notebook.mplstyle',
)

publicationstyle = (
    plt_styles_dir / 'publication.mplstyle',
)