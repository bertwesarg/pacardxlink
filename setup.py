from setuptools import setup

setup(
    name = 'pacardxlink',
    version = '1.1',
    author = 'Bert Wesarg',
    author_email = 'bertwesarg@users.noreply.github.com',
    description = 'A PulseAudio AppIndicator to cross link the inputs and outputs of two audio devices',
    license = '3-clause BSD',
    url = 'https://github.com/bertwesarg/pacardxlink',
    scripts = ['pacardxlink.py'],
    install_requires = [
        'pygtk>=2.24',
        'appindicator>=12.10.1',
        'pulsectl>=16.8.14'
    ]
)
