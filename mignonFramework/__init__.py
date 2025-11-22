
import importlib
import sys
from typing import TYPE_CHECKING


try:
    from .utils.utilClass.RunOnce import RunOnce
    from .utils.utilClass import color2Logo

    def printLogo():
        is_source_script = sys.argv and sys.argv[0].lower().endswith(('.py', '.pyw'))
        if not is_source_script:
            return

        mignonFrameworkPrint = """                                                         
           __     __)                      \u200ARex
          (, /|  /|   ,                         
            / | / |     _  __   _____
         ) /  |/  |__(_(_/_/ (_(_) / (_
        (_/   '       .-/              
                     (_/               
                                     v 0.5 mignonFramework
        """
        print(color2Logo.colorize_logo(mignonFrameworkPrint))

    RunOnce.execute(printLogo)
except ImportError:
    pass


if TYPE_CHECKING:
    from mignonFramework.utils.BackendAugmentation import RequestsMapping
    from mignonFramework.utils.Queues import QueueIter, target
    from mignonFramework.utils.Logger import Logger
    from mignonFramework.utils.config.SQLiteTracker import SQLiteTracker, TableId, injectSQLite, VarChar
    from mignonFramework.utils.utilClass.CountLinesInFolder import count_lines_in_single_file as countSingleFileLines, count_lines_in_files as countFolderFileLines, count_lines_in_directory as countDirectoryFileLines
    from mignonFramework.utils.utilClass.Deduplicate import deduplicate_file as deduplicateFile, read_and_write_lines as readLines2otherFiles, replace_line_with_file_content as replaceLineByFile, copy_line_by_number as copyLineByNumber
    from mignonFramework.utils.utilClass.PortForwarding import start_services as portForwordRun
    from mignonFramework.utils.utilClass.Curl2Request import CurlToRequestsConverter as Curl2Request
    from mignonFramework.utils.GenericProcessor import GenericFileProcessor as InsertQuick, Rename
    from mignonFramework.utils.ProcessFile import run as processRun
    from mignonFramework.utils.writer.MySQLManager import MysqlManager
    from mignonFramework.utils.reader.BaseReader import BaseReader
    from mignonFramework.utils.writer.BaseWriter import BaseWriter
    from mignonFramework.utils.config.ConfigReader import ConfigManager, inject
    from mignonFramework.utils.execJS.execJSTo import execJS
    from mignonFramework.utils.mignonFramework_starter import start
    from mignonFramework.utils.utilClass.JSONFormatter import JSONFormatter
    from mignonFramework.utils.utilClass.SqlDDL2List import extract_column_names_from_ddl as extractDDL2List
    from mignonFramework.utils.utilClass.getJSONequals import jsonContrast
    from mignonFramework.utils.execJS.MicroserviceByNodeJS import MicroServiceByNodeJS
    from mignonFramework.utils.config.JsonlConfigReader import JsonConfigManager, injectJson, ClassKey
    from mignonFramework.utils.utilClass.printDirectoryTree import print_directory_tree as printDirectoryTree
    from mignonFramework.utils.dataBaseTransfer import DatabaseTransferRunner, AbstractDatabaseTransfer, TransferConfig
    from mignonFramework.utils.Louru_Plus import LoguruPlus, SendLog
    from mignonFramework.utils.config.TomlConfigReader import injectToml, TomlConfigManager, ClassKey as TomlClassKey

__lazy_mapping__ = {
    'TomlClassKey':('mignonFramework.utils.config.TomlConfigReader', 'ClassKey'),
    'injectToml':('mignonFramework.utils.config.TomlConfigReader', 'injectToml'),
    'TomlConfigManager':('mignonFramework.utils.config.TomlConfigReader', 'TomlConfigManager'),
    'RequestsMapping': ('mignonFramework.utils.BackendAugmentation.RequestsMapping', 'RequestsMapping'),
    'countSingleFileLines': ('mignonFramework.utils.utilClass.CountLinesInFolder', 'count_lines_in_single_file'),
    'countFolderFileLines': ('mignonFramework.utils.utilClass.CountLinesInFolder', 'count_lines_in_files'),
    'countDirectoryFileLines': ('mignonFramework.utils.utilClass.CountLinesInFolder', 'count_lines_in_directory'),
    'deduplicateFile': ('mignonFramework.utils.utilClass.Deduplicate', 'deduplicate_file'),
    'readLines2otherFiles': ('mignonFramework.utils.utilClass.Deduplicate', 'read_and_write_lines'),
    'replaceLineByFile': ('mignonFramework.utils.utilClass.Deduplicate', 'replace_line_with_file_content'),
    'copyLineByNumber': ('mignonFramework.utils.utilClass.Deduplicate', 'copy_line_by_number'),
    'portForwordRun': ('mignonFramework.utils.utilClass.PortForwarding', 'start_services'),
    'Curl2Request': ('mignonFramework.utils.utilClass.Curl2Request', 'CurlToRequestsConverter'),
    'InsertQuick': ('mignonFramework.utils.GenericProcessor', 'GenericFileProcessor'),
    'Rename': ('mignonFramework.utils.GenericProcessor', 'Rename'),
    'processRun': ('mignonFramework.utils.ProcessFile', 'run'),
    'extractDDL2List': ('mignonFramework.utils.utilClass.SqlDDL2List', 'extract_column_names_from_ddl'),
    'printDirectoryTree': ('mignonFramework.utils.utilClass.printDirectoryTree', 'print_directory_tree'),
    'injectJson': ('mignonFramework.utils.config.JsonlConfigReader', 'injectJson'),
    'ClassKey': ('mignonFramework.utils.config.JsonlConfigReader', 'ClassKey'),
    'QueueIter': ('mignonFramework.utils.Queues', 'QueueIter'),
    'target': ('mignonFramework.utils.Queues', 'target'),
    'Logger': ('mignonFramework.utils.Logger', 'Logger'),
    'SQLiteTracker': ('mignonFramework.utils.config.SQLiteTracker', 'SQLiteTracker'),
    'TableId': ('mignonFramework.utils.config.SQLiteTracker', 'TableId'),
    'injectSQLite': ('mignonFramework.utils.config.SQLiteTracker', 'injectSQLite'),
    'VarChar': ('mignonFramework.utils.config.SQLiteTracker', 'VarChar'),
    'MysqlManager': ('mignonFramework.utils.writer.MySQLManager', 'MysqlManager'),
    'BaseReader': ('mignonFramework.utils.reader.BaseReader', 'BaseReader'),
    'BaseWriter': ('mignonFramework.utils.writer.BaseWriter', 'BaseWriter'),
    'ConfigManager': ('mignonFramework.utils.config.ConfigReader', 'ConfigManager'),
    'inject': ('mignonFramework.utils.config.ConfigReader', 'inject'),
    'execJS': ('mignonFramework.utils.execJS.execJSTo', 'execJS'),
    'start': ('mignonFramework.utils.mignonFramework_starter', 'start'),
    'JSONFormatter': ('mignonFramework.utils.utilClass.JSONFormatter', 'JSONFormatter'),
    'jsonContrast': ('mignonFramework.utils.utilClass.getJSONequals', 'jsonContrast'),
    'MicroServiceByNodeJS': ('mignonFramework.utils.execJS.MicroserviceByNodeJS', 'MicroServiceByNodeJS'),
    'JsonConfigManager': ('mignonFramework.utils.config.JsonlConfigReader', 'JsonConfigManager'),
    'DatabaseTransferRunner': ('mignonFramework.utils.dataBaseTransfer', 'DatabaseTransferRunner'),
    'AbstractDatabaseTransfer': ('mignonFramework.utils.dataBaseTransfer', 'AbstractDatabaseTransfer'),
    'TransferConfig': ('mignonFramework.utils.dataBaseTransfer', 'TransferConfig'),
    'LoguruPlus': ('mignonFramework.utils.Louru_Plus', 'LoguruPlus'),
    'SendLog': ('mignonFramework.utils.Louru_Plus', 'SendLog'),
}


def __getattr__(name: str):
    if name in __lazy_mapping__:
        module_path, original_name = __lazy_mapping__[name]
        try:
            module = importlib.import_module(module_path)
            attribute = getattr(module, original_name)
            setattr(sys.modules[__name__], name, attribute)
            return attribute
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import '{name}' from '{module_path}'.") from e
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    existing_attributes = list(globals().keys())
    lazy_attributes = list(__lazy_mapping__.keys())
    return sorted(existing_attributes + lazy_attributes)