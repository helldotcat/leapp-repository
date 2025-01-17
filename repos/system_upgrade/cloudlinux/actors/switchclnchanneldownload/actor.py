from leapp.actors import Actor
from leapp.libraries.stdlib import api
from leapp.tags import DownloadPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import CalledProcessError
from leapp.libraries.common.cllaunch import run_on_cloudlinux
from leapp.libraries.common.cln_switch import cln_switch
from leapp import reporting
from leapp.reporting import Report


class SwitchClnChannelDownload(Actor):
    """
    Switch CLN channel from 7 to 8 to be able to download upgrade packages.
    """

    name = "switch_cln_channel_download"
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, DownloadPhaseTag.Before)

    @run_on_cloudlinux
    def process(self):
        try:
            cln_switch(target=8)
        except CalledProcessError as e:
            reporting.create_report(
                [
                    reporting.Title(
                        "Failed to switch CloudLinux Network channel from 7 to 8."
                    ),
                    reporting.Summary(
                        "Command {} failed with exit code {}."
                        " The most probable cause of that is a problem with this system's"
                        " CloudLinux Network registration.".format(e.command, e.exit_code)
                    ),
                    reporting.Remediation(
                        hint="Check the state of this system's registration with \'rhn_check\'."
                        " Attempt to re-register the system with \'rhnreg_ks --force\'."
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Tags(
                        [reporting.Tags.OS_FACTS, reporting.Tags.AUTHENTICATION]
                    ),
                    reporting.Flags([reporting.Flags.INHIBITOR]),
                ]
            )
        except OSError as e:
            api.current_logger().error(
                "Could not call RHN command: Message: %s", str(e), exc_info=True
            )
