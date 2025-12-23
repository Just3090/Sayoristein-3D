









label splashscreen:






    python:

        renpy.save_persistent()

        config.allow_skipping = False

        basedir = config.basedir.replace("\\", "/")

    call screen shader_warmup

    jump sayoristein_main_menu

