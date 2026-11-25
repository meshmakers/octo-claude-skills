namespace Fixture.Commands;

internal abstract class JobWithWaitOctoCommand<T> : ServiceClientOctoCommand<T>
{
    protected JobWithWaitOctoCommand(ILogger logger, string group, string commandValue, string description)
        : base(logger, group, commandValue, description)
    {
        _waitForJobArg = CommandArgumentValue.AddArgument("w", "wait",
            ["Wait for the job to finish"], false, 0);
    }
}
