import numpy as np
import astropy

import pysiaf
import astropy.time, astropy.units as u, astropy.table

## Functions to retrieve on-board TA SAMs from observatory telemetry logs
## Developed in notebooks/Retrieve TA SAMS from OSS Logs.ipynb
#
#
# Because of the complexities & variation of different TA activity sequences per instrument mode,
# there's some complexity to parsing the messages and extracting the correct value. In particular,
# many TAs include dithers, and the logged value at the end of that process is the SAM to go from the
# last dither position back to the TA reference location. For WCS correction purposes we instead want
# to know what the corrective move would have been if taken from the initial pointing prior to any
# dithers. This can be computed as the vector sum of the dither move SAMs and the TA SAM; this value
# would be zero if there is no pointing offset prior to the dithers. I refer to this vector sum as the
# "net TA correction".
#
# Conceptually this code works by:
#
# 	* Retrieving the OSS logs and extracting the TA SAM values
#  	* Keeping track of any necessary book-keeping, added offsets, and/or other peculiarities
#       per each of the many kinds of onboard TA
# 	* Outputting the overall delta pointing which the TA process applied to center up on the TA target
# 	  (expressed as ∆V2, ∆V3 in observatory V frame coordinates, in arcsec)
#
#

from jwql.instrument_monitors.common_monitors.ta_monitor import guiding_analyses, mast
from jwql.instrument_monitors.common_monitors.ta_monitor.engdb import get_oss_log_messages


# The following is commented out to reduce code duplication, but can be uncommented if using this
# module as standalone code outside of misc_jwst
#
# def get_oss_log_messages(visitid):
#     """ Retrieve OSS event log messages during a given visit
#
#     Parameters
#     ----------
#     visitid : str
#         Visit ID string, like 'V01234001001'
#
#     Returns astropy Table containing the timestamps and message values
#     """
#
#     #----- When was that visit? -----
#     start_time, end_time = misc_jwst.mast.query_visit_time(visitid)
#     if start_time is None:
#         raise RuntimeError(f"Cannot find start time for visit {visitid}. That visit may not have happened yet.")
#
#     #----- Retrieve relevant messages from the ICTM event log stream -----
#     from jwst.lib.engdb_tools import ENGDB_Service
#     service = ENGDB_Service()  # By default, will use the public MAST service.
#
#     # There are multiple mnemonics we care about,
#     # in particular the EVENT_MSG has the text, and the MSG_ID and MSG_SRC give metadata on the source
#     # Retrieve all of these and organize into a table for convenience.
#
#     msg_times, messages = service.get_values("ICTM_EVENT_MSG", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)
#     msg_times_2, msg_ids = service.get_values("ICTM_EVENT_MSG_ID", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)
#     msg_times_3, msg_srcs = service.get_values("ICTM_EVENT_MSG_SRC", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)
#
#     #----- Arrange those 3 sets of results into a single Table -----
#     # Ideally we should have gotten the same number of rows in all 3 queries above\
#     # These -should- all have matching counts and time stamps... but for some reason this is not always the case. Hmm.
#     # So check here and if necessary handle the case of an inconsistency.
#
#     if len(messages) == len(msg_ids) and len(messages) == len(msg_srcs):
#         #print("consistent number of rows returned")
#         msg_table = astropy.table.Table([msg_times, messages, msg_ids, msg_srcs],
#                                        names = ['TIME', "EVENT_MSG", "EVENT_MSG_ID", "EVENT_MSG_SRC"])
#     else:
#         print("INconsistent number of EVENT_MSG and EVENT_MSG_ID records returned; matching based on telemetry time stamps ")
#         # This occurs for instance in visit V07344017001, a NIRCam WFSC visit.
#
#         msg_table = astropy.table.Table([msg_times[0:1], messages[0:1], msg_ids[0:1], msg_srcs[0:1]],
#                            names = ['TIME', "EVENT_MSG", "EVENT_MSG_ID", "EVENT_MSG_SRC"])
#         # match up the rows that do have consistent timestamps
#         # When there's not a match, look 1 row before or after to see if we can find a match
#         n = min(len(msg_times), len(msg_times_2), len(msg_times_3))
#         index_offset = 0  # We will use this to track offsets between mnemonic time series
#         for i in range(1, n):
#             # Compare time stamps between EVENT_MSG and EVENT_MSG_ID mnemonic time series
#             if msg_times[i] - msg_times_2[i+index_offset] == 0*u.second:
#                 # times match, no need to adjust
#                 pass
#             else:
#                 if msg_times[i] == msg_times_2[i+index_offset-1]:
#                     #print('found extra EVENT_MSG relative to EVENT_MSG_ID')
#                     index_offset -= 1
#                 elif msg_times[i] == msg_times_2[i+index_offset+1]:
#                     #print('found skipped EVENT_MSG relative to EVENT_MSG_ID')
#                     index_offset += 1
#                 else:
#                     raise RuntimeError("Inconsistent number of telemetry records returned, with bigger gaps than this function can currently sort out.")
#             msg_table.add_row([msg_times[i], messages[i], msg_ids[i+index_offset], msg_srcs[i+index_offset]])
#
#     return msg_table
#

# Constants
# OSS event log messages. ID numbers provided by Neville Shane.

MSGID_TA_ANALYSIS_START = 8210
MSGID_TA_ANALYSIS_END = 8210
MSGID_TA_DETECTOR = 8218
MSGID_TA_SAM_GENERIC = 8231
MSGID_TA_SAM_DITHER = 8232
MSGID_TA_NRC_CORON_OFFSET = 8248
MSGID_TA_SAM_NRS_WATA = 8230
MSGID_TA_SAM_NRS_MSATA = 8235
MSGID_TA_SAM_MSA_HALF_FACET = 8557
MSGID_TA_NIS_FAILURE = -8826

def get_messages_by_id(msg_table, msg_id):
    """Select a subset of event log messages matching a specified EVENT_MSG_ID
    """
    return msg_table['EVENT_MSG'].value[msg_table['EVENT_MSG_ID'] == msg_id]

def locate_messages_by_id(msg_table, msg_id):
    """ Return indices of event log messages matching a specified EVENT_MSG_ID
    """
    return np.where(msg_table['EVENT_MSG_ID'] == msg_id)


def which_instrument_ta(msg_table, verbose=True):
    """ Figure out which instrument was used for a given TA, based on the detector/aperture reported by OSS"""

    if (msg_table['EVENT_MSG_ID'] == MSGID_TA_ANALYSIS_START).sum() == 0:
        raise RuntimeError("Could not find start of TA messages. This visit may not have had TA?")

    message_with_det = get_messages_by_id(msg_table, MSGID_TA_DETECTOR)
    ta_detector = message_with_det[0].split()[-1]

    ta_inst = ta_detector[0:3]
    if verbose:
        print(f"TA aperture: {ta_detector}, therefore TA is using {ta_inst}")

    return ta_inst


def get_sam_xy(message):
    """ Given an OSS log message like 'TA SAM = 1.234, 5.679' extract the 2 numeric values as floats

    Returns a tuple with the x, y values
    """
    # take the last 2 entries in the line. Strip any punctuation in 'x, y' or '(x, y)'. Cast to floats
    return tuple( [float(m.strip(',()')) for m in message.split()[-2:] ])

def get_sam_xyr(message):
    """ Given an OSS log message like 'TA SAM = 1.234, 5.679, 10.123' extract the 3 numeric values as floats

    Returns a tuple with the x, y, r values
    """
    # take the last 3 entries in the line. Strip any punctuation in 'x, y' or '(x, y)'. Cast to floats
    return tuple( [float(m.strip(',()')) for m in message.split()[-3:] ])


def get_net_sam(messages):
    """ Given a series of N messages with SAMs, compute the overall net sum of the resulting summed SAM

    returns a tuple with the x, y values
    """
    moves = np.zeros((len(messages),2), float)
    for i, m in enumerate(messages):
        moves[i] = get_sam_xy(messages[i])
    net_correction = moves.sum(axis=0)
    return net_correction


def convert_sam_FGSideal_to_Vframe(delta_xy, which_guider, verbose=False):
    import pysiaf
    ap = pysiaf.Siaf('FGS').apertures[f'{which_guider}_FULL_OSS']

    # Note, we must rotate by the NEGATIVE of the angle, because we're rotating from the Idl frame BACK to V
    V3IdlYAngle_rad = np.deg2rad(ap.V3IdlYAngle)

    # conversion equations here provided by Matt Lallo:
    #   "Watch the parity (VIdlParity) For the _FULL Ideal frames it’s -1 (i.e. opposite handedness from V2,V3) for _OSS it’s +1.
    #   I believe the SAMs Ideal frame is the _FULL and not _OSS (which is only used by OSS as I intended it and understand it to be)."
    delta_v2 =  ap.VIdlParity * delta_xy[0] * np.cos(V3IdlYAngle_rad) + delta_xy[1] * np.sin(V3IdlYAngle_rad)
    delta_v3 = -ap.VIdlParity * delta_xy[0] * np.sin(V3IdlYAngle_rad) + delta_xy[1] * np.cos(V3IdlYAngle_rad)
    delta_v2v3 = np.array([delta_v2, delta_v3])

    if verbose:
        print(f"""    in {which_guider} Ideal frame: {delta_xy}
    rotate by {ap.V3IdlYAngle} deg to the V frame, with aperture parity {ap.VIdlParity}
    in V2V3 frame: {delta_v2v3}""")

    return delta_v2v3




# MIRI coronagraphy has some extra complications, which need additional functions to handle.

def retrieve_miri_coron_ta_apertures_used(visitid):
    """Look up from MAST the primary and secondary TA regions used in a given MIRI coronagraphy visit.
    MIRI coronagraphy uses a multi step process with two subregions, and the TA SAMs include a move between those
    subregions, which we have to take into account. Which subregions are used is not stated in the OSS log, so we
    need to look up that information from MAST or some other source to know how to proceed for a given MIRI coron visit.

    Parameters
    ----------
    visitid : str
        Visit ID, like 'V01234005006'

    Returns list of str aperture names, like ['MIRIM_TALYOT_UR', 'MIRIM_TALYOT_CUR']
    """
    program = int(visitid[1:6])
    observtn = int(visitid[6:9])

    ta_aper_info = mast.jwst_keywords_query('MIRI', program=program, observtn=observtn,
                                                      exp_type='MIR_TACQ', columns="filename, program, observtn, apername")
    ta_apertures_used = list(set(ta_aper_info['apername']))
    ta_apertures_used.sort()
    ta_apertures_used.reverse()
    return ta_apertures_used

def get_miri_offset_between_coron_ta_regions(visitid, verbose=False):
    """Determine the V2V3 vector offset from primary to secondary TA regions used in a given MIRI coronagraphy visit

    Parameters
    ----------
    visitid : str
        Visit ID, like 'V01234005006'

    Returns vector (∆V2, ∆V3) as numpy ndarray

    """
    # Which two TA apertures were used? Like ['MIRIM_TA1550_UR', 'MIRIM_TA1550_CUR']
    ta_apertures_used = retrieve_miri_coron_ta_apertures_used(visitid)
    if verbose:
        print("MIRI coron TA used apertures "+ ", ".join(ta_apertures_used))

    # Compute the vector offset between those
    ta_rois = [pysiaf.Siaf('MIRI').apertures[apname] for apname in ta_apertures_used]
    subregion_offset_v2v3 = np.asarray((ta_rois[1].V2Ref - ta_rois[0].V2Ref, ta_rois[1].V3Ref - ta_rois[0].V3Ref))

    return subregion_offset_v2v3



def parse_ta_log_messages_by_instrument(msg_table, which_guider, visitid, verbose = True):
    """ Given a table of TA messages, extract the values and compute the overall TA correction move

    Lots of cases here ad hoc to handle the many different TA activity sequences per instrument and mode.

    Returns (delta_V2, deltaV3), delta_roll

    """

    ta_inst = which_instrument_ta(msg_table, verbose=verbose)

    ta_delta_roll = 0       # True by default for all TA cases except NIRSpec MSATA
    ta_v2v3_offset = None   # Optional offset, special case which only applies to MSATA

    if ta_inst == 'MIR':
        # MIRI:
        # If config = MIR4QPM or MIRLYOT:
        #     SAM to move from ref point of block to primary ROI (Event Message 8231, “TA SAM (x, y) = …“)
        #     SAM to move to secondary ROI (8231)
        #     Final TA SAM to center of secondary ROI (8231)
        # Else if config = MIRLRS and subarray = SUBPRISM:
        #    SAM to move from ref point of block to primary ROI (8231)
        #     TA SAM to center of ROI (8231)
        # Else:
        #     TA SAM to center of ROI (8231)

        # MIRI has some variable number of TA sams
        ta_sams = get_messages_by_id(msg_table, MSGID_TA_SAM_GENERIC)

        if len(ta_sams) == 0:
            # TA must have failed
            print(f"No TA SAMs found for visit {visitid}; TA must have failed.")
            net_ta_correction = np.nan, np.nan
        elif len(ta_sams) == 1:
            ta_type = 'MIRI TA, undithered'
            # Simple MIRI TA, including MRS with TA. No dithers.
            net_ta_correction = get_sam_xy(ta_sams[0])
        elif len(ta_sams) == 2:
            ta_type = 'MIRI TA, LRS Slitless'
            # There will be 2 SAMs. The first is from the TA_BLOCK aperture to the TA aperture;
            # it's a constant SAM independent of pointing, not depending on any pixel values or measurements
            # The second SAM is the actual TA correction SAM made after the TA image is taken.
            net_ta_correction = get_sam_xy(ta_sams[1])

        elif len(ta_sams) == 3:
            ta_type = 'MIRI TA, coronagraphic'
            # There will be 3 SAMs. The first is from the TA_BLOCK aperture to the TA aperture;
            # it's a constant SAM independent of pointing, not depending on any pixel values or measurements
            # The second SAM is the first TA correction SAM made after the TA image in the primary aperture is taken.
            # it moves from the primary TA aperture to teh secondary TA aperture
            # The third SAM is a second corrective move in the secondary TA aperture
            # (There is a 4th SAM, external to the TA process, from the secondary TA aperture center to the coron reference point)
            # The overall correction is the sum of the second and third TA SAMs, minus the offset between the primary and secondary
            # TA apertures. That however depends on which apertures are being used, which isn't in the OSS log.
            # I don't know how to figure this out except from querying MAST to determine which apertures were used in this visit...

            net_ta_correction = get_net_sam(ta_sams[1:])  # ignore the first (0th) SAM from the TA Block region
            ta_v2v3_offset = -1 * get_miri_offset_between_coron_ta_regions(visitid, verbose=verbose)   # Note we want a sign flip here!
            ta_v2v3_offset_source = 'MIRI coron offset between TA subregions'


        if verbose:
            print(f"TA type: {ta_type}")
            print(f"MIRI TA used  {len(ta_sams)} TA sams")
            for i in range(len(ta_sams)):
                print("\t" + ta_sams[i])
            if ta_type in ['MIRI TA, LRS Slitless', 'MIRI TA, coronagraphic']:
                print("The first SAM above is from the TA_BLOCK region to TA region; we ignore that SAM for this calculation.")
            if ta_v2v3_offset is not None:
                print(f"Note the second SAM above includes the coron offset between TA subregions, which we should subtract out:")
                print(-ta_v2v3_offset, " in V2,V3")


    elif ta_inst == 'NRC':
        # NIRCam may have either (1) TA with no dithers or (2) TA with 3 images separated by 2 dithers.
        #
        # If ta_type = LOS:
        #    TA SAM to center of ROI (8231)
        # Else:
        #    SAM from 1st dither point to 2nd dither point (8232, “Dither SAM (x, y) = …”)
        #    SAM from 2nd dither point to 3rd dither point (8232)
        #    TA SAM calculation to center of ROI (8231)
        #    If coronagraphy TA:
        #        calculate the wedge offsets  (8248, “Correction to NRC SAM (x, y) = …”)
        #    The actual SAM move is the deltas shown in the 8231 message minus any wedge offsets from the 8248 message.

        ta_sam = get_messages_by_id(msg_table, MSGID_TA_SAM_GENERIC)

        # we need to check for dither SAMS looking ONLY at messages before the TA SAM
        # this is needed to exclude any dithers in the science visit
        ta_sam_index = locate_messages_by_id(msg_table, MSGID_TA_SAM_GENERIC)[0][0]

        dither_sams = get_messages_by_id(msg_table[0:ta_sam_index], MSGID_TA_SAM_DITHER)

        coron_offset = get_messages_by_id(msg_table, MSGID_TA_NRC_CORON_OFFSET)
        net_ta_correction = get_net_sam(np.hstack([dither_sams, ta_sam]))

        ta_type = "NRC with 3 dithers" if len(dither_sams) else "NRC without dithering"

        if len(coron_offset):
            ta_type += ", coronagraphic"
            # the sign is opposite for this one; we need to subtract it!
            offset_xy = get_sam_xy(coron_offset[0])
            net_ta_correction -= offset_xy

        if verbose:
            print(f"TA type: {ta_type}")
            print(f"NRC TA used {len(dither_sams)} dithers, {len(ta_sam)} TA sams, {len(coron_offset)} coron wedge offset correction")
            for i in range(len(dither_sams)):
                print("\t" + dither_sams[i])
            print("\t" + ta_sam[0])
            if len(coron_offset):
                print("\t" + coron_offset[0])

    elif ta_inst == 'NIS':
        # NIRISS TA always has 3 exposures separated by 2 dithers:
        #
        # SAM from 1st dither point to 2nd dither point (8232, “Dither SAM (x, y) = …”)
        # SAM from 2nd dither point to 3rd dither point (8232)
        # TA SAM to center of ROI (8231)

        # we expect 2 dithers and then the resulting correction move.
        # Note there may be additional dithers in the science visit AFTER the TA, so
        # we need to truncate the table when searching for dithers
        index_ta_end = locate_messages_by_id(msg_table, MSGID_TA_ANALYSIS_END)[0].min()
        dither_sams = get_messages_by_id(msg_table[:index_ta_end], MSGID_TA_SAM_DITHER)
        ta_sam = get_messages_by_id(msg_table, MSGID_TA_SAM_GENERIC)

        ta_failure = len(get_messages_by_id(msg_table, MSGID_TA_NIS_FAILURE) == 1)
        if ta_failure:
            net_ta_correction = np.asarray([0.0, 0.0])
            if verbose:
                print("TA failure. No TA correction applied.")
        else:
            if len(dither_sams) !=2 or len(ta_sam) !=1:
                # TA didn't fail, but we're having trouble parsing the messages
                raise RuntimeError(f"Did not find expected SAM messages for TA type = NIRISS. Expected 2 dither SAMss, found {len(dither_sams)}; expected 1 TA SAM, found {len(ta_sam)} ")

            print(dither_sams)
            print(ta_sam)
            net_ta_correction = get_net_sam(np.hstack([dither_sams, ta_sam]))

            if verbose:
                print('NIS TA always uses 2 dithers, then final TA SAM:')
                print("\t" + dither_sams[0])
                print("\t" + dither_sams[1])
                print("\t" + ta_sam[0])

    elif ta_inst == 'NRS':
        # NIRSpec can have either (1) BOTA/WATA TA without dithers, or (2) MSATA, with 1 dither:
        # If BOTA:
        #     TA SAM to center of ROI (8235, “TA SAM for NRS (x, y) = …”)
        # Else (MSA):
        #     Half facet SAM (8557, “NIRSpec TA MSA half facet SAM”).
        #          Values hard-coded in NRSDEFTA script in V2/V3 frame:
        #          MSA_HALFFACET_V2 = -0.27566, MSA_HALFFACET_V3 = 0.10979.
        #     TA SAM to center of ROI (8235, “TA SAM for NRS (x, y, r) = …”)

        # we expect maybe 1 half-facet dither and then the resulting correction move.
        dither_sams = get_messages_by_id(msg_table, MSGID_TA_SAM_MSA_HALF_FACET)

        if len(dither_sams):
            ta_type = 'NRS MSATA'
            ta_sam = get_messages_by_id(msg_table, MSGID_TA_SAM_NRS_MSATA)

            # We are dealing with an MSATA case. The TA SAM message will include an observatory roll.
            ta_v2v3_offset = (-0.27566, 0.10979)
            ta_v2v3_offset_source = 'NRS MSATA half-facet dither'
            # In this case the TA message will have a nonzero delta roll too.
            net_ta_with_roll = get_sam_xyr(ta_sam[0])
            net_ta_correction, ta_delta_roll = net_ta_with_roll[0:2], net_ta_with_roll[2]

        else:
            ta_type = 'NRS WATA'
            ta_sam = get_messages_by_id(msg_table, MSGID_TA_SAM_NRS_WATA)

            net_ta_correction = get_net_sam(ta_sam)


        if verbose:
            print(f"TA type: {ta_type}")
            print(f"NRS TA used {len(dither_sams)} dithers, {len(ta_sam)} TA sam")
            if len(dither_sams):
                print(f'    NIRSpec half-facet dither SAM. Hard coded to (∆V2, ∆V3) = {ta_v2v3_offset}')

            print("    " + ta_sam[0])

    if verbose:
        print("NET TA CORRECTION:", net_ta_correction, f"arcsecs in {which_guider} ideal frame")

    ta_correction_v2v3 = convert_sam_FGSideal_to_Vframe(net_ta_correction, which_guider, verbose=verbose)

    if verbose:
        print("TA CORRECTION:    ", ta_correction_v2v3, f"arcsecs in V2V3 frame")

    if ta_v2v3_offset is not None:
        ta_correction_v2v3 += ta_v2v3_offset
        if verbose:
            print(f"Taking into account the additional offset in V2V3 from {ta_v2v3_offset_source}")
            print("TA CORRECTION:    ", ta_correction_v2v3, f"arcsecs in V2V3 frame")

    if verbose:
        print("TA DELTA ROLL:", ta_delta_roll, "arcseconds")

    return ta_correction_v2v3, ta_delta_roll


def get_ta_correction_for_visit(visitid, verbose=True, msg_table=None):
    """Top level function to retrieve TA messages and extract the overall TA correction SAM

    Returns (delta_V2, deltaV3), delta_roll
    """

    if msg_table is None:
        msg_table = get_oss_log_messages(visitid)

    which_guider = guiding_analyses.which_guider_used(visitid)
    if verbose:
        print(f"Visit {visitid} used guider {which_guider}")

    return parse_ta_log_messages_by_instrument(msg_table, which_guider, visitid, verbose=verbose)

