# This piece of physics comes from Post's 1995 paper
# "Calculations of Energy Losses due to Atomic Processes in
#  Tokamaks with Applications to the ITER Divertor"
#
# we determine Equation 2's integral.
#
# Note that compared to Kallenbach's 2013 paper, "Impurity seeding for
# tokamak power exhaust: from present devices via ITER to DEMO",
# the Post calculation ignores the lowered conductivity due
# to higher Z_eff, which ends up lowering the total radiated power.

import numpy as np

import atomic
import scipy.integrate

def temperatureRange(ad, top=1e3):
    """Get the temperature range to integrate for an element.

    We expect recombination at around half the first ionisation
    energy, so the integral should be from there upwards.
    """
    first_ion=ad.coeffs['ionisation_potential'](0,10,1e19)
    return np.logspace(np.log10(first_ion/2.0), np.log10(top), 25)

def post_integral(ad, temperature, electron_density, tau=np.inf, powertype='total'):
    """\int_{T[0]}^{T} Lz(Te) Te^{1/2} \;dTe

    Lz is given in W m^3 so the output has units of [W m^3 eV^{1/2}]

    Arguments:
        ad (AtomicData): data for this species
        temperature (np.array): list of temperatures to integrate up to.
        electron_density (float): background electron density in m^{-3}.
        tau (float): time constant for diffusion of impurities. The default,
            infinity, uses a faster collisional-radiative equilibrium solver.
        powertype (optional, string): for the finite n_e * tau case,
            whether to use all electron cooling power for Lz, or just radiation. 
            sensible values: 'rad_total', 'total'. Default is 'total'.
    Returns:
        A 1D np.array corresponding to integral up to various temperatures.
    """
    if tau == np.inf:
        eq = atomic.CollRadEquilibrium(ad)
        y = eq.ionisation_stage_distribution(temperature, electron_density)
        Lz = atomic.Radiation(y).specific_power['total']
    else:
        rt = atomic.RateEquationsWithDiffusion(ad)
        times = np.logspace(-7, np.log10(tau)+1, 40)
        times -= times[0]
        yy = rt.solve(times, temperature, electron_density, tau)
        Lz = atomic.ElectronCooling(yy.abundances[-1]).specific_power[powertype]
    Lzint = scipy.integrate.cumtrapz(Lz * np.sqrt(temperature),
            x=temperature, initial=0)
    return Lzint

def rhs(ad, temperature, electron_density, tau=np.inf, powertype='total', kappa0=3125.):
    """The rhs of Post's equation (2).

    He is using Lz in units of ergs cm^3 s.
    One of those equals 10^{-13} W m^3.

    Arguments:
        ad (AtomicData): data for this species
        temperature (np.array): list of temperatures to integrate up to
        electron_density (float): background electron density in m^{-3}.
        tau (float): time constant for diffusion of impurities.
        powertype (optional, string): for the finite n_e * tau case,
            whether to report all electron cooling power or just radiation. 
            sensible values: 'rad_total', 'total'. Default is 'total'.
        kappa0: (float) the parallel thermal conductivity. From analysis of
            Post's paper it appears he is using kappa_0 = 31000/ln(\Lambda)
            and ln(\Lambda) = 9.92, so 3125 or something.
    Returns:
        A 1D np.array corresponding to the rhs at various
            upstream temperatures.
    """
    lzint = post_integral(ad, temperature, electron_density, tau, powertype)
    kappa_factor = np.sqrt(kappa0/3125.0) * 2.5e5
    return kappa_factor * np.sqrt(temperature ** 2 * (lzint * 1e13) )
